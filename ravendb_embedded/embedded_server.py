from __future__ import annotations
import atexit
import logging
import os
import queue
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, List, Callable, Tuple, Generic, TypeVar, Dict, IO
from threading import Lock, RLock, Thread
from queue import Queue
import webbrowser

from ravendb import DocumentStore, CreateDatabaseOperation
from ravendb.exceptions.raven_exceptions import ConcurrencyException, RavenException
from ravendb.tools.utils import Stopwatch
from ravendb_embedded.options import ServerOptions, DatabaseOptions
from ravendb_embedded.raven_server_runner import RavenServerRunner

_T = TypeVar("_T")


@dataclass(frozen=True)
class ServerProcessExitedEvent:
    process_id: int
    exit_code: int
    expected: bool


class EmbeddedServer:
    END_OF_STREAM_MARKER = "$$END_OF_STREAM$$"

    # singleton
    def __init__(self):
        self.server_task: Optional[Lazy[Tuple[str, subprocess.Popen]]] = None
        self._server_options: Optional[ServerOptions] = None
        self._lifecycle_lock = RLock()
        self._exit_handler: Optional[Callable[[], None]] = None
        self._process_exit_lock = RLock()
        self._process_exit_callbacks: List[Callable[[ServerProcessExitedEvent], None]] = []
        self._watched_processes = set()
        self._expected_process_exits = set()
        self.document_stores = {}
        self._document_stores_lock = RLock()
        self.client_pem_certificate_path: Optional[str] = None
        self.trust_store_path: Optional[str] = None
        self._graceful_shutdown_timeout: Optional[timedelta] = None
        self._process_kill_timeout: Optional[timedelta] = None
        self.logger = logging.Logger(self.__class__.__name__, logging.DEBUG)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _log_debug(self, message: str) -> None:
        if not self.logger.disabled and self.logger.isEnabledFor(logging.DEBUG):
            self.logger.log(logging.DEBUG, message)

    def add_server_process_exited(self, callback: Callable[[ServerProcessExitedEvent], None]) -> None:
        if not callable(callback):
            raise ValueError("callback must be callable")
        with self._process_exit_lock:
            if callback not in self._process_exit_callbacks:
                self._process_exit_callbacks.append(callback)

    def remove_server_process_exited(self, callback: Callable[[ServerProcessExitedEvent], None]) -> None:
        with self._process_exit_lock:
            if callback in self._process_exit_callbacks:
                self._process_exit_callbacks.remove(callback)

    def start_server(self, options_param: ServerOptions = None) -> None:
        options = options_param or ServerOptions()

        with self._lifecycle_lock:
            if self.server_task is not None:
                raise RuntimeError("The server was already started")

            self._server_options = options
            self._graceful_shutdown_timeout = options.graceful_shutdown_timeout
            self._process_kill_timeout = options.process_kill_timeout

            start_server = Lazy(lambda: self._run_server(options))
            self.server_task = start_server

            if options.security is not None:
                self.client_pem_certificate_path = options.security.client_pem_certificate_path
                self.trust_store_path = options.security.ca_certificate_path

            try:
                start_server.get_value()
            except Exception:
                if self.server_task is start_server:
                    self.server_task = None
                    self._server_options = None
                self._unregister_exit_handler()
                raise

    def get_document_store(self, database: str) -> DocumentStore:
        return self.get_document_store_from_options(DatabaseOptions.from_database_name(database))

    def _initialize_document_store(self, database_name, options):
        server_url = self.get_server_uri()

        store = DocumentStore(server_url, database_name)
        if self.client_pem_certificate_path:
            store.certificate_pem_path = self.client_pem_certificate_path
        store.trust_store_path = self.trust_store_path
        store.conventions = options.conventions

        def remove_store():
            with self._document_stores_lock:
                self.document_stores.pop(database_name, None)

        store.add_after_close(remove_store)

        store.initialize()

        if not options.skip_creating_database:
            self._try_create_database(options, store)

        return store

    def get_document_store_from_options(self, options: DatabaseOptions) -> DocumentStore:
        database_name = options.database_record.database_name
        if not database_name or database_name.isspace():
            raise ValueError("DatabaseName cannot be null or whitespace")

        with self._lifecycle_lock:
            if self.server_task is None:
                raise RuntimeError("Please run start_server() before trying to use the server.")

            self._log_debug(f"Creating document store for '{database_name}'.")

            with self._document_stores_lock:
                lazy = self.document_stores.get(database_name)
                if lazy is None:
                    lazy = Lazy(lambda: self._initialize_document_store(database_name, options))
                    self.document_stores[database_name] = lazy

            return lazy.get_value()

    def _try_create_database(self, options: DatabaseOptions, store: DocumentStore) -> None:
        try:
            store.maintenance.server.send(CreateDatabaseOperation(options.database_record))
        except ConcurrencyException:
            self._log_debug(f"{options.database_record.database_name} already exists.")

    def get_server_uri(self) -> str:
        with self._lifecycle_lock:
            server = self.server_task
            if server is None:
                raise RuntimeError("Please run start_server() before trying to use the server.")

            return server.get_value()[0]

    def get_server_process_id(self) -> int:
        with self._lifecycle_lock:
            server = self._require_started_server("get_server_process_id")
            return server.get_value()[1].pid

    def stop_server(self) -> None:
        with self._lifecycle_lock:
            server = self._require_started_server("stop_server")
            self._unregister_exit_handler()
            self._shutdown_server_process(server.get_value()[1])

    def restart_server(self) -> None:
        with self._lifecycle_lock:
            existing_server = self._require_started_server("restart_server")
            options = self._server_options

            self._unregister_exit_handler()
            try:
                self._shutdown_server_process(existing_server.get_value()[1])
            except Exception:
                pass

            if self.server_task is not existing_server:
                raise RuntimeError("The server changed while restarting it")

            restarted_server = Lazy(lambda: self._run_server(options))
            self.server_task = restarted_server
            try:
                restarted_server.get_value()
            except Exception:
                if self.server_task is restarted_server:
                    self.server_task = None
                self._unregister_exit_handler()
                raise

    def _require_started_server(self, operation: str) -> Lazy[Tuple[str, subprocess.Popen]]:
        server = self.server_task
        if self._server_options is None or server is None or not server.created:
            raise RuntimeError(f"Cannot call {operation}() before calling start_server()")
        return server

    def _shutdown_server_process(self, process: subprocess.Popen) -> None:
        if not process:
            return

        try:
            if process.poll() is not None:
                return

            self._mark_process_exit_expected(process)
            graceful_timeout = (self._graceful_shutdown_timeout or timedelta(seconds=30)).total_seconds()
            kill_timeout = (self._process_kill_timeout or timedelta(seconds=5)).total_seconds()

            try:
                self._log_debug("Trying to shut down the server gracefully.")
                if process.stdin is None:
                    raise RuntimeError("The server process stdin is not available.")

                process.stdin.write(b"shutdown no-confirmation\n")
                process.stdin.flush()
                process.wait(timeout=graceful_timeout)
                return
            except Exception as error:
                self._log_debug(
                    f"Failed to gracefully shut down the server in {self._graceful_shutdown_timeout}. Error: {error}"
                )

            if process.poll() is not None:
                return

            try:
                self._log_debug("Terminating the server process.")
                process.terminate()
                process.wait(timeout=kill_timeout)
                return
            except subprocess.TimeoutExpired:
                self._log_debug(f"The server did not terminate in {self._process_kill_timeout}; killing it.")
            except Exception as error:
                self._log_debug(f"Failed to terminate the server process. Error: {error}")

            if process.poll() is not None:
                return

            try:
                process.kill()
                process.wait(timeout=kill_timeout)
            except Exception as error:
                self._log_debug(f"Failed to kill the server process in {self._process_kill_timeout}. Error: {error}")
        finally:
            if process.poll() is not None:
                self._close_process_streams(process)

    @staticmethod
    def _close_process_streams(process: subprocess.Popen) -> None:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is None or stream.closed:
                continue
            try:
                stream.close()
            except Exception:
                pass

    def _register_exit_handler(self, process: subprocess.Popen) -> None:
        self._unregister_exit_handler()
        self._exit_handler = lambda: self._shutdown_server_process(process)
        atexit.register(self._exit_handler)

    def _watch_server_process(self, process: subprocess.Popen) -> None:
        with self._process_exit_lock:
            self._watched_processes.add(process.pid)

        def watch():
            exit_code = process.wait()
            with self._process_exit_lock:
                expected = process.pid in self._expected_process_exits
                self._expected_process_exits.discard(process.pid)
                self._watched_processes.discard(process.pid)
                callbacks = list(self._process_exit_callbacks)

            event = ServerProcessExitedEvent(process.pid, exit_code, expected)
            for callback in callbacks:
                try:
                    callback(event)
                except Exception as error:
                    self._log_debug(f"Server process exit callback failed. Error: {error}")

        Thread(target=watch, daemon=True, name=f"ravendb-process-{process.pid}").start()

    def _mark_process_exit_expected(self, process: subprocess.Popen) -> None:
        with self._process_exit_lock:
            if process.pid in self._watched_processes:
                self._expected_process_exits.add(process.pid)

    def _unregister_exit_handler(self) -> None:
        if self._exit_handler is None:
            return
        atexit.unregister(self._exit_handler)
        self._exit_handler = None

    def _run_server(self, options: ServerOptions) -> Tuple[str, subprocess.Popen]:
        try:
            if options.clear_target_server_location:
                shutil.rmtree(options.target_server_location, ignore_errors=True)

            options.provider.provide(options.target_server_location)
        except Exception as e:
            message = (
                f"Failed to spawn server files.{os.linesep}Path: '{options.target_server_location}'{os.linesep}{e}"
            )
            self._log_debug(message)
            raise RuntimeError(message) from e

        process = RavenServerRunner.run(options)

        self._log_debug("Starting global server")

        url_ref: Dict[str, Optional[str]] = {"value": None}
        startup_duration = Stopwatch.create_started()

        output_string = self.read_output(
            process.stdout,
            startup_duration,
            options,
            lambda line, builder: self.online(line, builder, url_ref, process, startup_duration, options),
        )

        if url_ref["value"] is None:
            error_string = self.read_output(process.stderr, Stopwatch.create_started(), options, None)
            self._shutdown_server_process(process)
            raise RuntimeError(self.build_startup_exception_message(output_string, error_string, process))

        self._register_exit_handler(process)
        self._watch_server_process(process)
        return url_ref["value"], process

    @staticmethod
    def build_startup_exception_message(output_string: str, error_string: str, process: subprocess.Popen) -> str:
        sb = ["Unable to start the RavenDB Server", os.linesep]

        if process.args:
            sb.append("Command:")
            sb.append(os.linesep)
            sb.append(" ".join(process.args))
            sb.append(os.linesep)

        if error_string:
            sb.append("Error:")
            sb.append(os.linesep)
            sb.append(error_string)
            sb.append(os.linesep)

        if output_string:
            sb.append("Output:")
            sb.append(os.linesep)
            sb.append(output_string)
            sb.append(os.linesep)

        sb.append("Check your ServerOptions and host dependencies, or run the command manually to see detailed error.")
        return "".join(sb)

    def online(
        self,
        line: str,
        builder: List[str],
        url_ref: Dict[str, Optional[str]],
        process: subprocess.Popen,
        startup_duration: Stopwatch,
        options: ServerOptions,
    ):
        if line is None:
            error_string = self.read_output(process.stderr, Stopwatch.create_started(), options, None)
            self._shutdown_server_process(process)
            raise RuntimeError(self.build_startup_exception_message("".join(builder), error_string, process))

        prefix = "Server available on: "
        if line.startswith(prefix):
            url_ref["value"] = line[len(prefix) :]
            return True

        return False

    def read_output(
        self,
        output: IO,
        startup_duration: Stopwatch,
        options: ServerOptions,
        online: Optional[Callable[[str, List[str]], bool]],
    ):
        def read_output_line() -> Optional[str]:
            while True:
                try:
                    line_ = output_queue.get_nowait()
                    return line_
                except queue.Empty:
                    if options.max_server_startup_time_duration - startup_duration.elapsed() <= timedelta(seconds=0):
                        return None
                    time.sleep(1)

        def output_reader():
            try:
                for line_ in iter(output.readline, b""):
                    output_queue.put(line_.decode("utf-8").strip())
                output_queue.put(self.END_OF_STREAM_MARKER)
            except Exception as e:
                raise RavenException("Unable to read server output") from e

        output_queue: Queue[str] = Queue()
        output_thread = Thread(target=output_reader, daemon=True)
        output_thread.start()

        sb = []

        while True:
            line = read_output_line()

            if options.max_server_startup_time_duration < startup_duration.elapsed():
                return "".join(sb)

            if line is None:
                break

            if line == self.END_OF_STREAM_MARKER:
                break

            sb.append(line)
            sb.append(os.linesep)

            should_stop = False
            if online is not None:
                should_stop = online(line, sb)

            if should_stop:
                break

        return "".join(sb)

    def open_studio_in_browser(self):
        server_url = self.get_server_uri()

        try:
            webbrowser.open(server_url)
        except Exception as e:
            raise RuntimeError(e)

    def close(self):
        with self._lifecycle_lock:
            lazy = self.server_task
            if lazy is None or not lazy.created:
                return

            self.server_task = None
            self._unregister_exit_handler()
            process = lazy.get_value()[1]
            self._shutdown_server_process(process)

            with self._document_stores_lock:
                stores = list(self.document_stores.values())

                for value in stores:
                    if value.created:
                        value.get_value().close()

                self.document_stores.clear()

            self._server_options = None
            self.client_pem_certificate_path = None
            self.trust_store_path = None


class Lazy(Generic[_T]):
    def __init__(self, func: Callable[[], _T]):
        self.func = func
        self._value = None
        self._created = False
        self._lock = Lock()

    def get_value(self) -> _T:
        if not self._created:
            with self._lock:
                if not self._created:
                    self._value = self.func()
                    self._created = True
        return self._value

    @property
    def created(self):
        with self._lock:
            return self._created
