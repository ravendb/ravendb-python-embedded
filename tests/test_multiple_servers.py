import tempfile
from pathlib import Path
from unittest import TestCase

from ravendb_embedded import EmbeddedServer, ServerOptions


class TestMultipleServers(TestCase):
    def test_independent_servers_can_run_in_the_same_process(self):
        with tempfile.TemporaryDirectory() as directory:
            first_options = self._options(directory, "first")
            second_options = self._options(directory, "second")

            with EmbeddedServer() as first_server, EmbeddedServer() as second_server:
                first_server.start_server(first_options)
                second_server.start_server(second_options)

                self.assertNotEqual(first_server.get_server_process_id(), second_server.get_server_process_id())
                self.assertNotEqual(first_server.get_server_uri(), second_server.get_server_uri())

                with first_server.get_document_store("SharedName") as first_store:
                    with first_store.open_session() as session:
                        session.store({"server": "first"}, "markers/1")
                        session.save_changes()

                with second_server.get_document_store("SharedName") as second_store:
                    with second_store.open_session() as session:
                        self.assertIsNone(session.load("markers/1", dict))
                        session.store({"server": "second"}, "markers/1")
                        session.save_changes()

                with first_server.get_document_store("SharedName") as first_store:
                    with first_store.open_session() as session:
                        self.assertEqual("first", session.load("markers/1", dict)["server"])

    @staticmethod
    def _options(root: str, name: str) -> ServerOptions:
        options = ServerOptions()
        options.accept_eula = True
        options.data_directory = str(Path(root, name, "data"))
        options.logs_path = str(Path(root, name, "logs"))
        return options
