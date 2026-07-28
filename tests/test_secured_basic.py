import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from ravendb_embedded.embedded_server import EmbeddedServer
from ravendb_embedded.options import ServerOptions, DatabaseOptions
from ravendb_embedded.provide import CopyServerFromNugetProvider
from tests import Person
from tests.certificates import generate_self_signed_certificates


class TestSecuredBasic(TestCase):
    def test_secured_embedded(self):
        temp_dir = tempfile.mkdtemp()
        try:
            server_pfx, client_pem, ca_crt = generate_self_signed_certificates(temp_dir)
            with EmbeddedServer() as embedded:
                server_options = ServerOptions()
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
