import shutil
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

from ravendb_embedded.embedded_server import EmbeddedServer
from ravendb_embedded.options import ServerOptions, DatabaseOptions
from ravendb_embedded.provide import CopyServerFromNugetProvider
from tests import Person
from tests.certificates import generate_self_signed_certificates, generate_separate_server_and_client_certificates


class TestSecuredBasic(TestCase):
    def test_secured_embedded(self):
        temp_dir = tempfile.mkdtemp()
        try:
            server_pfx, client_pem, ca_crt = generate_self_signed_certificates(temp_dir)
            with EmbeddedServer() as embedded:
                server_options = ServerOptions()
                server_options.accept_eula = True
                server_options.secured(server_pfx, client_pem, ca_certificate_path=ca_crt)
                server_options.data_directory = str(Path(temp_dir, "RavenDB"))
                server_options.logs_path = str(Path(temp_dir, "Logs"))
                server_options.provider = CopyServerFromNugetProvider()
                embedded.start_server(server_options)

                database_options = DatabaseOptions.from_database_name("Test")

                with embedded.get_document_store_from_options(database_options) as store:
                    with store.open_session() as session:
                        person = Person()
                        person.name = "Gracjan"

                        session.store(person, "people/1")
                        session.save_changes()
        finally:
            shutil.rmtree(temp_dir)

    def test_secured_embedded_with_separate_admin_certificate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server_pfx, client_pem, ca_crt = generate_separate_server_and_client_certificates(temp_dir)
            with EmbeddedServer() as embedded:
                server_options = ServerOptions()
                server_options.accept_eula = True
                server_options.secured(server_pfx, client_pem, ca_certificate_path=ca_crt)
                server_options.data_directory = str(Path(temp_dir, "RavenDB"))
                server_options.logs_path = str(Path(temp_dir, "Logs"))
                server_options.provider = CopyServerFromNugetProvider()
                embedded.start_server(server_options)

                with embedded.get_document_store("Test") as store:
                    with store.open_session() as session:
                        person = Person()
                        person.name = "Separate admin certificate"
                        session.store(person, "people/1")
                        session.save_changes()

    def test_secured_embedded_with_certificate_exec(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server_pfx, client_pem, ca_crt = generate_separate_server_and_client_certificates(temp_dir)
            certificate_loader = Path(temp_dir, "load_certificate.py")
            certificate_loader.write_text(
                "import pathlib\n"
                "import sys\n"
                "sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())\n",
                encoding="utf-8",
            )

            with EmbeddedServer() as embedded:
                server_options = ServerOptions()
                server_options.accept_eula = True
                server_options.secured_with_certificate_exec(
                    sys.executable,
                    f'"{certificate_loader}" "{server_pfx}"',
                    client_pem,
                    ca_certificate_path=ca_crt,
                )
                server_options.data_directory = str(Path(temp_dir, "RavenDB"))
                server_options.logs_path = str(Path(temp_dir, "Logs"))
                server_options.provider = CopyServerFromNugetProvider()
                embedded.start_server(server_options)

                with embedded.get_document_store("Test") as store:
                    with store.open_session() as session:
                        person = Person()
                        person.name = "Certificate loader"
                        session.store(person, "people/1")
                        session.save_changes()
