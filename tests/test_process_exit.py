import sys
import tempfile
from pathlib import Path
from threading import Event
from unittest import TestCase

from ravendb_embedded import EmbeddedServer, ServerOptions


class TestProcessExit(TestCase):
    @staticmethod
    def server_options(directory, script):
        server_directory = Path(directory, "Server")
        server_directory.mkdir()
        Path(server_directory, "Raven.Server.dll").write_text(script, encoding="utf-8")

        options = ServerOptions()
        options.with_external_server(str(server_directory))
        options.dot_net_path = sys.executable
        options.data_directory = str(Path(directory, "data"))
        options.logs_path = str(Path(directory, "logs"))
        return options

    def test_reports_unexpected_process_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            options = self.server_options(
                directory,
                "import sys\n"
                "print('Server available on: http://127.0.0.1:12345', flush=True)\n"
                "raise SystemExit(23)\n",
            )
            callback_finished = Event()
            events = []

            with EmbeddedServer() as server:
                def on_exit(event):
                    events.append(event)
                    callback_finished.set()

                server.add_server_process_exited(on_exit)
                server.start_server(options)
                process_id = server.get_server_process_id()

                self.assertTrue(callback_finished.wait(10))

            self.assertEqual(1, len(events))
            self.assertEqual(process_id, events[0].process_id)
            self.assertEqual(23, events[0].exit_code)
            self.assertFalse(events[0].expected)

    def test_reports_expected_process_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            options = self.server_options(
                directory,
                "import sys\n"
                "print('Server available on: http://127.0.0.1:12345', flush=True)\n"
                "sys.stdin.readline()\n",
            )
            callback_finished = Event()
            events = []

            with EmbeddedServer() as server:
                server.add_server_process_exited(
                    lambda event: (events.append(event), callback_finished.set())
                )
                server.start_server(options)
                process_id = server.get_server_process_id()
                server.stop_server()

                self.assertTrue(callback_finished.wait(10))

            self.assertEqual(1, len(events))
            self.assertEqual(process_id, events[0].process_id)
            self.assertEqual(0, events[0].exit_code)
            self.assertTrue(events[0].expected)
