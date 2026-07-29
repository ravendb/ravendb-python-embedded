import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from ravendb_embedded.embedded_server import EmbeddedServer
from ravendb_embedded.options import ServerOptions, DatabaseOptions
from ravendb_embedded.provide import CopyServerFromNugetProvider
from tests import Person


class TestCustomProvider(TestCase):
    @staticmethod
    def configure_server_options(temp_dir: str, server_options: ServerOptions) -> ServerOptions:
        server_options.accept_eula = True
        server_options.target_server_location = str(Path(temp_dir, "RavenDBServer"))
        server_options.data_directory = str(Path(temp_dir, "RavenDB"))
        server_options.logs_path = str(Path(temp_dir, "Logs"))
        server_options.command_line_args = ["--Features.Availability=Experimental"]
        return server_options

    def test_can_use_zip_as_external_server_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Zip the bundled server so the test does not depend on cwd or a pre-built archive.
            server_zip = shutil.make_archive(
                str(Path(temp_dir, "ravendb-server")),
                "zip",
                CopyServerFromNugetProvider().server_files,
            )
            with EmbeddedServer() as embedded:
                server_options = ServerOptions()
                server_options = self.configure_server_options(temp_dir, server_options)
                server_options.with_external_server(server_zip)
                embedded.start_server(server_options)

                database_options = DatabaseOptions.from_database_name("Test")

                with embedded.get_document_store_from_options(database_options) as store:
                    with store.open_session() as session:
                        loaded_person = session.load("no-such-person", Person)
                        self.assertIsNone(loaded_person)

    def test_can_use_directory_as_external_server_source(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            with EmbeddedServer() as embedded:
                server_options = ServerOptions()
                server_options = self.configure_server_options(temp_directory, server_options)
                server_options.with_external_server(CopyServerFromNugetProvider().server_files)
                embedded.start_server(server_options)

                database_options = DatabaseOptions.from_database_name("Test")

                with embedded.get_document_store_from_options(database_options) as store:
                    with store.open_session() as session:
                        loaded_person = session.load("no-such-person", Person)
                        self.assertIsNone(loaded_person)

    def test_can_use_default_nuget_provider(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            with EmbeddedServer() as embedded:
                options = self.configure_server_options(temp_directory, ServerOptions())
                database_options = DatabaseOptions.from_database_name("Test")
                embedded.start_server(options)
                with embedded.get_document_store_from_options(database_options) as store:
                    with store.open_session() as session:
                        loaded_person = session.load("no-such-person", Person)
                        self.assertIsNone(loaded_person)
