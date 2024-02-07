import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from ravendb_embedded.embedded_server import EmbeddedServer
from ravendb_embedded.options import ServerOptions, DatabaseOptions
from ravendb_embedded.provide import CopyServerFromNugetProvider
from tests import Person


class BasicTest(TestCase):
    def test_embedded(self):
        temp_dir = tempfile.mkdtemp()
        try:
            with EmbeddedServer() as embedded:
                server_options = ServerOptions()
                server_options.target_server_location = str(Path(temp_dir, "RavenDBServer"))
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
                server_options.target_server_location = str(Path(temp_dir, "RavenDBServer"))
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
