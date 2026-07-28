import tempfile
from pathlib import Path
from unittest import TestCase

from ravendb_embedded import CopyServerFromNugetProvider, EmbeddedServer, ServerOptions


class TestLifecycle(TestCase):
    def test_lifecycle_methods_require_a_started_server(self):
        server = EmbeddedServer()

        for operation in (
            server.get_server_process_id,
            server.stop_server,
            server.restart_server,
        ):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(
                    RuntimeError,
                    rf"Cannot call {operation.__name__}\(\) before calling start_server\(\)",
                ):
                    operation()

    def test_stop_and_restart_real_server(self):
        with tempfile.TemporaryDirectory() as directory:
            options = ServerOptions()
            options.data_directory = str(Path(directory, "RavenDB"))
            options.logs_path = str(Path(directory, "Logs"))
            options.provider = CopyServerFromNugetProvider()

            with EmbeddedServer() as server:
                server.start_server(options)
                first_process = server.server_task.get_value()[1]
                first_pid = server.get_server_process_id()

                server.stop_server()

                self.assertEqual(first_pid, first_process.pid)
                self.assertIsNotNone(first_process.poll())

                server.restart_server()
                second_pid = server.get_server_process_id()

                self.assertNotEqual(first_pid, second_pid)
                with server.get_document_store("Lifecycle") as store:
                    with store.open_session() as session:
                        session.store({"Status": "restarted"}, "lifecycle/1")
                        session.save_changes()
