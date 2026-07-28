from __future__ import annotations
import atexit
import logging
import os
import queue
import shutil
import subprocess
import time
from datetime import timedelta
from typing import Optional, List, Callable, Tuple, Generic, TypeVar, Dict, IO
from threading import Thread
from queue import Queue
import webbrowser

from ravendb import DocumentStore, CreateDatabaseOperation
from ravendb.exceptions.raven_exceptions import RavenException
from ravendb.tools.utils import Stopwatch
from ravendb_embedded.options import ServerOptions, DatabaseOptions
from ravendb_embedded.raven_server_runner import RavenServerRunner

_T = TypeVar("_T")


class EmbeddedServer:
    END_OF_STREAM_MARKER = "$$END_OF_STREAM$$"

    # singleton
    def __init__(self):
        self.server_task: Optional[Lazy[Tuple[str, subprocess.Popen]]] = None
        self.document_stores = {}
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

    def start_server(self, options_param: ServerOptions = None) -> None:
        options = options_param or ServerOptions()

        self._graceful_shutdown_timeout = options.graceful_shutdown_timeout
        self._process_kill_timeout = options.process_kill_timeout

        start_server = Lazy(lambda: self._run_server(options))

        if self.server_task and self.server_task.created and self.server_task != start_server:
            raise RuntimeError("The server was already started")

        self.server_task = start_server

        if options.security is not None:
            self.client_pem_certificate_path = options.security.client_pem_certificate_path
            self.trust_store_path = options.security.ca_certificate_path

        start_server.get_value()

    def get_document_store(self, database: str) -> DocumentStore:
        return self.get_document_store_from_options(DatabaseOptions.from_database_name(database))

    def _initialize_document_store(self, database_name, options):
        server_url = self.get_server_uri()

        store = DocumentStore(server_url, database_name)
        if self.client_pem_certificate_path:
            store.certificate_pem_path = self.client_pem_certificate_path
        store.trust_store_path = self.trust_store_path
        store.conventions = options.conventions

        store.add_after_close(lambda: self.document_stores.pop(database_name, None))

        store.initialize()

        if not options.skip_creating_database:
            self._try_create_database(options, store)

        return store

    def get_document_store_from_options(self, options: DatabaseOptions) -> DocumentStore:
        database_name = options.database_record.database_name

        if not database_name or database_name.isspace():
            raise ValueError("DatabaseName cannot be null or whitespace")

        self._log_debug(f"Creating document store for '{database_name}'.")

        lazy = Lazy(lambda: self._initialize_document_store(database_name, options))

        return self.document_stores.setdefault(database_name, lazy).get_value()

    def _try_create_database(self, options: DatabaseOptions, store: DocumentStore) -> None:
        try:
            store.maintenance.server.send(CreateDatabaseOperation(options.database_record))
        except Exception as e:
            # Expected behavior when the database already exists
            if "conflict" in e.args[0] or "already exists" in e.args[0]:
                self._log_debug(f"{options.database_record.database_name} already exists.")
            else:
                raise e

    def get_server_uri(self) -> str:
        server = self.server_task
        if server is None:
            raise RuntimeError("Please run start_server() before trying to use the server.")

        return server.get_value()[0]

    def _shutdown_server_process(self, process: subprocess.Popen) -> None:
        if not process or process.poll() is not None:
            return

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

        atexit.register(lambda: self._shutdown_server_process(process))

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
        lazy = self.server_task
        if lazy is None or not lazy.created:
            return

        process = lazy.get_value()[1]
        self._shutdown_server_process(process)

        for value in list(self.document_stores.values()):
            if value.created:
                value.get_value().close()

        self.document_stores.clear()
        self.server_task = None


class Lazy(Generic[_T]):
    def __init__(self, func: Callable[[], _T]):
        self.func = func
        self._value = None
        self._created = False

    def get_value(self) -> _T:
        if not self._created:
            self._value = self.func()
            self._created = True
        return self._value

    @property
    def created(self):
        return self._created
