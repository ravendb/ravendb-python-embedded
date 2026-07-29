import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import TestCase

from ravendb_embedded import EmbeddedServer, ServerOptions, ServerStartupError, ServerStartupTimeoutError


class TestStartupErrors(TestCase):
    def test_failed_start_can_be_retried_on_the_same_server(self):
        with tempfile.TemporaryDirectory() as directory:
            server_directory = Path(directory, "Server")
            server_directory.mkdir()
            first_attempt = Path(directory, "first-attempt")
            Path(server_directory, "Raven.Server.dll").write_text(
                "import pathlib\n"
                "import sys\n"
                f"marker = pathlib.Path({str(first_attempt)!r})\n"
                "if not marker.exists():\n"
                "    marker.touch()\n"
                "    print('intentional first-start failure', file=sys.stderr, flush=True)\n"
                "    raise SystemExit(1)\n"
                "print('Server available on: http://127.0.0.1:12345', flush=True)\n"
                "sys.stdin.readline()\n",
                encoding="utf-8",
            )

            options = ServerOptions()
            options.accept_eula = True
            options.with_external_server(str(server_directory))
            options.dot_net_path = sys.executable
            options.framework_version = ""
            options.data_directory = str(Path(directory, "data"))
            options.logs_path = str(Path(directory, "logs"))

            with EmbeddedServer() as server:
                with self.assertRaises(ServerStartupError):
                    server.start_server(options)

                server.start_server(options)
                self.assertEqual("http://127.0.0.1:12345", server.get_server_uri())

    def test_startup_timeout_has_a_distinct_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            server_directory = Path(directory, "Server")
            server_directory.mkdir()
            Path(server_directory, "Raven.Server.dll").write_text(
                "import time\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )

            options = ServerOptions()
            options.accept_eula = True
            options.with_external_server(str(server_directory))
            options.dot_net_path = sys.executable
            options.framework_version = ""
            options.data_directory = str(Path(directory, "data"))
            options.logs_path = str(Path(directory, "logs"))
            options.max_server_startup_time_duration = timedelta(milliseconds=200)
            options.graceful_shutdown_timeout = timedelta(milliseconds=100)
            options.process_kill_timeout = timedelta(seconds=1)

            with EmbeddedServer() as server:
                with self.assertRaises(ServerStartupTimeoutError) as context:
                    server.start_server(options)

            self.assertIn("Server failed to start in 0.2 seconds.", str(context.exception))

    def test_stderr_is_drained_before_and_after_server_is_online(self):
        with tempfile.TemporaryDirectory() as directory:
            server_directory = Path(directory, "Server")
            server_directory.mkdir()
            shutdown_marker = Path(directory, "shutdown.txt")
            Path(server_directory, "Raven.Server.dll").write_text(
                "import pathlib\n"
                "import sys\n"
                "payload = 'x' * (1024 * 1024)\n"
                "sys.stderr.write(payload)\n"
                "sys.stderr.flush()\n"
                "print('Server available on: http://127.0.0.1:12345', flush=True)\n"
                "sys.stderr.write(payload)\n"
                "sys.stderr.flush()\n"
                "command = sys.stdin.readline().strip()\n"
                f"pathlib.Path({str(shutdown_marker)!r}).write_text(command, encoding='utf-8')\n",
                encoding="utf-8",
            )

            options = ServerOptions()
            options.accept_eula = True
            options.with_external_server(str(server_directory))
            options.dot_net_path = sys.executable
            options.framework_version = ""
            options.data_directory = str(Path(directory, "data"))
            options.logs_path = str(Path(directory, "logs"))
            options.max_server_startup_time_duration = timedelta(seconds=10)

            with EmbeddedServer() as server:
                server.start_server(options)

            self.assertEqual("shutdown no-confirmation", shutdown_marker.read_text(encoding="utf-8"))

    def test_failed_server_process_includes_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            server_directory = Path(directory, "Server")
            server_directory.mkdir()
            Path(server_directory, "Raven.Server.dll").write_text(
                "import sys\n"
                "sys.stdout.write('intentional stdout before failure\\n')\n"
                "sys.stdout.flush()\n"
                "sys.stderr.write('intentional startup failure from child process\\n')\n"
                "raise SystemExit(23)\n",
                encoding="utf-8",
            )

            options = ServerOptions()
            options.accept_eula = True
            options.with_external_server(str(server_directory))
            options.dot_net_path = sys.executable
            options.framework_version = ""
            options.data_directory = str(Path(directory, "data"))
            options.logs_path = str(Path(directory, "logs"))
            options.max_server_startup_time_duration = timedelta(seconds=10)

            with EmbeddedServer() as server:
                with self.assertRaises(ServerStartupError) as context:
                    server.start_server(options)

            message = str(context.exception)
            self.assertIn("Unable to start the RavenDB Server", message)
            self.assertIn("Error:", message)
            self.assertIn("intentional startup failure from child process", message)
            self.assertIn("Output:", message)
            self.assertIn("intentional stdout before failure", message)
