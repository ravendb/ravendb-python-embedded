from pyravendb.custom_exceptions.exceptions import InvalidOperationException, NotSupportedException
from pyravendb.raven_operations.server_operations import CreateDatabaseOperation
from pyravendb.store.document_store import DocumentStore

from pyravendb_embedded.ravenserver_runner import RavenServerRunner
from pyravendb_embedded.database_options import DatabaseOptions
from pyravendb_embedded.tools.helpers import PropagatingThread
from pyravendb_embedded.server_options import ServerOptions
from pyravendb_embedded.tools.helpers import singleton

from urllib.parse import urlparse
from datetime import datetime
from threading import Lock
import subprocess
import logging
import signal
import sys
import os

# create a file handler
handler = logging.FileHandler('Embedded.log')
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


@singleton
class EmbeddedServer:

    def __init__(self):
        self._certificate = None
        self._document_stores = {}
        self._document_stores_lock = Lock()
        self._server_task = None
        self.lock = Lock()
        self._certificate = None
        self.logger = logging.getLogger("Embedded")
        self.logger.setLevel(logging.INFO)
        # add the handlers to the logger
        self.logger.addHandler(handler)
        self._process = None
        self._gracefully_exit_timeout = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self._server_task is None:
            return

        _, process = self._server_task.join()
        with self.lock:
            self._server_task = None
        self._kill_slaved_server_process(process)

        with self._document_stores_lock:
            for _, value in self._document_stores.items():
                value.close()
            self._document_stores.clear()

    def start_server(self, server_options=None):
        if server_options is None:
            server_options = ServerOptions()

        self._gracefully_exit_timeout = server_options.gracefully_exit_timeout

        start_server = PropagatingThread(target=self._run_server, args=(server_options,), daemon=True)
        with self.lock:
            if self._server_task is not None:
                raise InvalidOperationException("The server was already started")
            self._server_task = start_server

        if server_options.security:
            self._certificate = server_options.security.client_certificate

        self._server_task.start()

    def _run_server(self, server_options):
        process = RavenServerRunner.run(server_options)
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info("Starting global server: " + str(process.pid))

        log = []
        start = datetime.now()
        while True:
            line = process.stdout.readline()
            if datetime.now() - start > server_options.max_server_startup_time_duration:
                break

            log.append(line + os.linesep)
            if not line:
                raise InvalidOperationException("Unable to start server, log is: " + os.linesep + " ".join(log))

            if "Server available on" in line:
                server_url = urlparse(line[len("Server available on: "):].rstrip())
                break

        if not server_url:
            self._kill_slaved_server_process(process)
            raise InvalidOperationException("Unable to start server, log is: " + os.linesep + " ".join(log))

        return server_url, process

    def get_server_url(self):
        server = self._server_task
        if not server:
            raise InvalidOperationException("Please run start_server() before trying to use the server")

        url, _ = server.join()
        return url

    def _try_create_database(self, database_options, store):
        try:
            store.maintenance.server.send(CreateDatabaseOperation(database_name=database_options.database_name))
        except Exception as e:
            # Expected behaviour when the database is already exists
            if "already exists!" in str(e):
                if self.logger.isEnabledFor(logging.INFO):
                    self.logger.info("Database {0} already exists".format(database_options.database_name))
            else:
                raise

    def get_document_store(self, database_data) -> DocumentStore:
        """
        Get the document store for working in the embedded

        :param database_data: Can be DatabaseOptions or just the name of the database
        :type database_data: DatabaseOptions or str

        :return: DocumentStore
        """

        if isinstance(database_data, str):
            database_data = DatabaseOptions(database_data)

        database_name = database_data.database_name

        if not database_name:
            raise ValueError("The database name is mandatory")

        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info("Creating document store for {0}.".format(database_name))

        def _create_document_store():
            server_url = self.get_server_url()
            store = DocumentStore(urls=[server_url.geturl()], database=database_name, certificate=self._certificate)
            store.initialize()

            if not database_data.skip_creating_database:
                self._try_create_database(database_data, store)

            yield store

        with self._document_stores_lock:
            return next(self._document_stores.setdefault(database_name, _create_document_store()))

    def _kill_slaved_server_process(self, process: subprocess.Popen):
        if process is None or process.poll():
            return
        try:
            process.communicate("q\ny\n", timeout=self._gracefully_exit_timeout)
        except subprocess.TimeoutExpired:
            try:
                if self.logger.isEnabledFor(logging.INFO):
                    self.logger.info("Killing global server PID {0}.".format(process.pid))
                process.kill()
            except Exception as e:
                if self.logger.isEnabledFor(logging.INFO):
                    self.logger.info("Failed to kill process {0}".format(process.pid), e)

    def open_studio_in_browser(self):
        server_url = self.get_server_url()
        if sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
            subprocess.Popen('cmd "/c start \"Stop & look at studio\" \"{0}\"'.format(server_url.geturl()))
        elif sys.platform.startswith("linux"):
            subprocess.Popen('xdg-open ' + server_url.geturl())
        elif sys.platform.startswith('darwin'):
            subprocess.Popen('open ' + server_url.geturl())
        else:
            raise NotSupportedException(
                "This action is not supported by you operation system ({0})".format(sys.platform))
