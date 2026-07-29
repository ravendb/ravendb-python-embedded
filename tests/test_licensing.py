import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

from ravendb_embedded import EmbeddedServer, ServerOptions


class TestLicensing(TestCase):
    def test_eula_acceptance_remains_enabled_by_default(self):
        self.assertTrue(ServerOptions().accept_eula)

    def test_server_receives_all_licensing_options(self):
        with tempfile.TemporaryDirectory() as directory:
            server_directory = Path(directory, "Server")
            server_directory.mkdir()
            arguments_file = Path(directory, "arguments.json")
            Path(server_directory, "Raven.Server.dll").write_text(
                "import json\n"
                "import pathlib\n"
                "import sys\n"
                f"pathlib.Path({str(arguments_file)!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n"
                "print('Server available on: http://127.0.0.1:12345', flush=True)\n"
                "sys.stdin.readline()\n",
                encoding="utf-8",
            )

            options = ServerOptions()
            options.with_external_server(str(server_directory))
            options.dot_net_path = sys.executable
            options.framework_version = ""
            options.data_directory = str(Path(directory, "data"))
            options.logs_path = str(Path(directory, "logs"))
            options.licensing.license = '{"Id":"test-license"}'
            options.licensing.license_path = str(Path(directory, "license.json"))
            options.licensing.disable_auto_update = True
            options.licensing.disable_auto_update_from_api = True
            options.licensing.disable_license_support_check = False
            options.licensing.throw_on_invalid_or_missing_license = True

            with EmbeddedServer() as server:
                server.start_server(options)

            arguments = json.loads(arguments_file.read_text(encoding="utf-8"))
            self.assertIn("--License.Eula.Accepted=true", arguments)
            self.assertIn("--License.DisableAutoUpdate=true", arguments)
            self.assertIn("--License.DisableAutoUpdateFromApi=true", arguments)
            self.assertIn("--License.DisableLicenseSupportCheck=false", arguments)
            self.assertIn("--License.ThrowOnInvalidOrMissingLicense=true", arguments)
            self.assertIn('--License={"Id":"test-license"}', arguments)
            self.assertIn(f"--License.Path={options.licensing.license_path}", arguments)
