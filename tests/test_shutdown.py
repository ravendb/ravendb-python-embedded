import sys
import tempfile
from pathlib import Path
from unittest import TestCase

from ravendb_embedded import EmbeddedServer, ServerOptions


class TestShutdown(TestCase):
    def test_close_sends_graceful_shutdown_command(self):
        with tempfile.TemporaryDirectory() as directory:
            server_directory = Path(directory, "Server")
            server_directory.mkdir()
            shutdown_marker = Path(directory, "graceful-shutdown.txt")
            Path(server_directory, "Raven.Server.dll").write_text(
                "import pathlib\n"
                "import sys\n"
                "print('Server available on: http://127.0.0.1:12345', flush=True)\n"
                "command = sys.stdin.readline().strip()\n"
                f"pathlib.Path({str(shutdown_marker)!r}).write_text(command, encoding='utf-8')\n",
                encoding="utf-8",
            )

            options = ServerOptions()
            options.with_external_server(str(server_directory))
            options.dot_net_path = sys.executable
            options.data_directory = str(Path(directory, "data"))
            options.logs_path = str(Path(directory, "logs"))

            server = EmbeddedServer()
            server.start_server(options)
            server.close()

            self.assertEqual("shutdown no-confirmation", shutdown_marker.read_text(encoding="utf-8"))
