import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest import TestCase

from ravendb_embedded import EmbeddedServer, ServerOptions


class TestShutdown(TestCase):
    def test_concurrent_start_launches_one_server(self):
        with tempfile.TemporaryDirectory() as directory:
            server_directory = Path(directory, "Server")
            server_directory.mkdir()
            start_marker = Path(directory, "starts.txt")
            Path(server_directory, "Raven.Server.dll").write_text(
                "import pathlib\n"
                "import sys\n"
                f"with pathlib.Path({str(start_marker)!r}).open('a', encoding='utf-8') as marker:\n"
                "    marker.write('started\\n')\n"
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
            server = EmbeddedServer()
            barrier = Barrier(8)

            def start():
                barrier.wait()
                try:
                    server.start_server(options)
                    return "started"
                except RuntimeError as error:
                    return str(error)

            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(lambda _: start(), range(8)))

            server.close()

            self.assertEqual(1, results.count("started"))
            self.assertEqual(7, results.count("The server was already started"))
            self.assertEqual(["started"], start_marker.read_text(encoding="utf-8").splitlines())

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
            options.accept_eula = True
            options.with_external_server(str(server_directory))
            options.dot_net_path = sys.executable
            options.framework_version = ""
            options.data_directory = str(Path(directory, "data"))
            options.logs_path = str(Path(directory, "logs"))

            server = EmbeddedServer()
            server.start_server(options)
            process = server.server_task.get_value()[1]
            server.close()

            self.assertEqual("shutdown no-confirmation", shutdown_marker.read_text(encoding="utf-8"))
            self.assertTrue(process.stdin.closed)
            self.assertTrue(process.stdout.closed)
            self.assertTrue(process.stderr.closed)
            self.assertIsNone(server._exit_handler)
