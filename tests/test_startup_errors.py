import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import TestCase

from ravendb_embedded import EmbeddedServer, ServerOptions


class TestStartupErrors(TestCase):
    def test_failed_server_process_includes_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            server_directory = Path(directory, "Server")
            server_directory.mkdir()
            Path(server_directory, "Raven.Server.dll").write_text(
                "import sys\n"
                "sys.stderr.write('intentional startup failure from child process\\n')\n"
                "raise SystemExit(23)\n",
                encoding="utf-8",
            )

            options = ServerOptions()
            options.with_external_server(str(server_directory))
            options.dot_net_path = sys.executable
            options.data_directory = str(Path(directory, "data"))
            options.logs_path = str(Path(directory, "logs"))
            options.max_server_startup_time_duration = timedelta(seconds=10)

            with EmbeddedServer() as server:
                with self.assertRaises(RuntimeError) as context:
                    server.start_server(options)

            message = str(context.exception)
            self.assertIn("Unable to start the RavenDB Server", message)
            self.assertIn("Error:", message)
            self.assertIn("intentional startup failure from child process", message)
