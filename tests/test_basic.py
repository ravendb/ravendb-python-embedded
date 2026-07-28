import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Thread
from unittest import TestCase

from ravendb_embedded import EmbeddedServer, ServerOptions, CopyServerFromNugetProvider, DatabaseOptions
from tests import Person


class BasicTest(TestCase):
    def test_close_waits_for_document_store_initialization(self):
        initialization_started = Event()
        continue_initialization = Event()
        close_finished = Event()
        results = {}
        errors = []

        class PausingEmbeddedServer(EmbeddedServer):
            def _initialize_document_store(self, database_name, options):
                initialization_started.set()
                continue_initialization.wait()
                return super()._initialize_document_store(database_name, options)

        with tempfile.TemporaryDirectory() as temp_dir:
            embedded = PausingEmbeddedServer()
            server_options = ServerOptions()
            server_options.data_directory = str(Path(temp_dir, "RavenDB"))
            server_options.logs_path = str(Path(temp_dir, "Logs"))
            server_options.provider = CopyServerFromNugetProvider()
            embedded.start_server(server_options)

            def get_store():
                try:
                    results["store"] = embedded.get_document_store("ConcurrentClose")
                except Exception as error:
                    errors.append(error)

            def close_server():
                try:
                    embedded.close()
                except Exception as error:
                    errors.append(error)
                finally:
                    close_finished.set()

            get_thread = Thread(target=get_store, daemon=True)
            close_thread = Thread(target=close_server, daemon=True)
            get_thread.start()
            self.assertTrue(initialization_started.wait(10))
            close_thread.start()

            self.assertFalse(close_finished.wait(0.2))
            continue_initialization.set()
            get_thread.join(30)
            close_thread.join(30)

            self.assertFalse(get_thread.is_alive())
            self.assertFalse(close_thread.is_alive())
            self.assertEqual([], errors)
            self.assertTrue(results["store"].disposed)

    def test_concurrent_calls_share_one_document_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with EmbeddedServer() as embedded:
                server_options = ServerOptions()
                server_options.data_directory = str(Path(temp_dir, "RavenDB"))
                server_options.logs_path = str(Path(temp_dir, "Logs"))
                server_options.provider = CopyServerFromNugetProvider()
                embedded.start_server(server_options)

                with ThreadPoolExecutor(max_workers=8) as executor:
                    stores = list(executor.map(lambda _: embedded.get_document_store("Shared"), range(8)))

                self.assertEqual(1, len({id(store) for store in stores}))
                stores[0].close()

    def test_close_disposes_open_document_stores(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            embedded = EmbeddedServer()
            server_options = ServerOptions()
            server_options.data_directory = str(Path(temp_dir, "RavenDB"))
            server_options.logs_path = str(Path(temp_dir, "Logs"))
            server_options.provider = CopyServerFromNugetProvider()
            embedded.start_server(server_options)

            first = embedded.get_document_store("First")
            second = embedded.get_document_store("Second")

            embedded.close()

            self.assertTrue(first.disposed)
            self.assertTrue(second.disposed)
            self.assertEqual({}, embedded.document_stores)
            self.assertIsNone(embedded.server_task)

    def test_embedded(self):
        temp_dir = tempfile.mkdtemp()
        try:
            with EmbeddedServer() as embedded:
                server_options = ServerOptions()
                server_options.data_directory = str(Path(temp_dir, "RavenDB"))
                server_options.logs_path = str(Path(temp_dir, "Logs"))
                server_options.provider = CopyServerFromNugetProvider()
                server_options.command_line_args = ["--Features.Availability=Experimental"]
                embedded.start_server(server_options)

                database_options = DatabaseOptions.from_database_name("Test")
                database_options.conventions.save_enums_as_integers = True

                with embedded.get_document_store_from_options(database_options) as store:
                    self.assertTrue(store.conventions.save_enums_as_integers)
                    self.assertTrue(store.get_request_executor().conventions.save_enums_as_integers)

                    with store.open_session() as session:
                        person = Person()
                        person.name = "John"

                        session.store(person, "people/1")
                        session.save_changes()

            with EmbeddedServer() as embedded:
                server_options = ServerOptions()
                server_options.data_directory = str(Path(temp_dir, "RavenDB"))
                server_options.provider = CopyServerFromNugetProvider()
                embedded.start_server(server_options)

                with embedded.get_document_store("Test") as store:
                    self.assertFalse(store.conventions.save_enums_as_integers)
                    self.assertFalse(store.get_request_executor().conventions.save_enums_as_integers)

                    with store.open_session() as session:
                        person = session.load("people/1", Person)

                        self.assertIsNotNone(person)
                        self.assertEqual(person.name, "John")

        finally:
            shutil.rmtree(temp_dir)
