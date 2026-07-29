import io
import importlib
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest import TestCase

from ravendb_embedded.embedded_server import EmbeddedServer
from ravendb_embedded.options import ServerOptions, DatabaseOptions
from ravendb_embedded.provide import (
    CopyServerFromNugetProvider,
    ExtractFromPkgResourceServerProvider,
    ExtractFromZipServerProvider,
)
from tests import Person


class TestCustomProvider(TestCase):
    def test_can_extract_server_from_a_package_resource(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            package_directory = Path(temp_directory, "example_server_package")
            package_directory.mkdir()
            Path(package_directory, "__init__.py").touch()
            resource = Path(package_directory, "server.zip")
            with zipfile.ZipFile(resource, "w") as zipped:
                zipped.writestr("Server/Raven.Server.dll", "server")

            sys.path.insert(0, temp_directory)
            importlib.invalidate_caches()
            try:
                destination = Path(temp_directory, "extracted")
                ExtractFromPkgResourceServerProvider(
                    "example_server_package",
                    "server.zip",
                ).provide(str(destination))
                self.assertTrue(Path(destination, "Server", "Raven.Server.dll").is_file())
            finally:
                sys.modules.pop("example_server_package", None)
                sys.path.remove(temp_directory)
                importlib.invalidate_caches()

    def test_external_zip_rejects_path_traversal(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("../escaped.txt", "unsafe")

        with tempfile.TemporaryDirectory() as temp_directory:
            destination = Path(temp_directory, "server")
            destination.mkdir()

            with self.assertRaisesRegex(RuntimeError, "unsafe archive path"):
                ExtractFromZipServerProvider.unzip(archive.getvalue(), str(destination))

            self.assertFalse(Path(temp_directory, "escaped.txt").exists())

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
