import tempfile
from pathlib import Path
from unittest import TestCase

from ravendb_embedded.options import ServerOptions
from ravendb_embedded.runtime_framework_version_matcher import (
    RuntimeFrameworkVersionMatcher,
    RuntimeFrameworkVersion,
)


class TestRuntimeFrameworkVersionMatcher(TestCase):
    def test_match_1(self):
        self.assertEqual("auto", ServerOptions().framework_version)

        options = ServerOptions()

        options.framework_version = None
        self.assertIsNone(RuntimeFrameworkVersionMatcher.match(options))

        options.framework_version = ""
        self.assertEqual("", RuntimeFrameworkVersionMatcher.match(options))

    def test_match_2(self):
        runtimes = self.get_runtimes()

        runtime = RuntimeFrameworkVersion("3.1.1")
        self.assertEqual(RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes), "3.1.1")

        runtime = RuntimeFrameworkVersion("2.1.11")
        self.assertEqual(RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes), "2.1.11")

        runtime = RuntimeFrameworkVersion("3.1.x")
        self.assertEqual(RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes), "3.1.3")

        runtime = RuntimeFrameworkVersion("3.x")
        self.assertEqual(RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes), "3.2.3")

        runtime = RuntimeFrameworkVersion("3.x.x")
        self.assertEqual(RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes), "3.2.3")

        runtime = RuntimeFrameworkVersion("5.0.x")
        self.assertEqual(RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes), "5.0.4")

        runtime = RuntimeFrameworkVersion("x")
        self.assertEqual(RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes), "5.0.4")

        runtime = RuntimeFrameworkVersion("5.0.x-rc.2.20475.17")
        self.assertEqual(
            RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes),
            "5.0.0-rc.2.20475.17",
        )

        runtime = RuntimeFrameworkVersion("6.x")

        with self.assertRaises(RuntimeError):
            RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes)

    def test_match_3(self):
        runtime = RuntimeFrameworkVersion("3.1.0-rc")
        self.assertEqual(str(runtime), "3.1.0-rc")

        runtime = RuntimeFrameworkVersion("5.0.0-rc.2.20475.17")
        self.assertEqual(str(runtime), "5.0.0-rc.2.20475.17")

    def test_match_4(self):
        runtimes = self.get_runtimes()

        runtime = RuntimeFrameworkVersion("3.1.1+")
        self.assertEqual(str(runtime), "3.1.1+")
        self.assertEqual(RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes), "3.1.3")

        runtime = RuntimeFrameworkVersion("3.1.4+")
        self.assertEqual(str(runtime), "3.1.4+")

        with self.assertRaises(RuntimeError) as context:
            RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes)
        self.assertIn(
            "Could not find a matching runtime for '3.1.4+'. Available runtimes:",
            str(context.exception),
        )
        self.assertIn("\n- 5.0.4\n- 5.0.3\n- 5.0.0-rc.2.20475.17", str(context.exception))

        with self.assertRaises(RuntimeError) as context:
            RuntimeFrameworkVersion("6.0.0+-preview.6.21352.12")
        self.assertIn(
            "Cannot set 'patch' with value '0+' because '+' is not allowed when suffix ('preview.6.21352.12') is set",
            str(context.exception),
        )

        with self.assertRaises(RuntimeError) as context:
            RuntimeFrameworkVersion("6+")
        self.assertIn(
            "Cannot set 'major' with value '6+' because '+' is not allowed.",
            str(context.exception),
        )

        with self.assertRaises(RuntimeError) as context:
            RuntimeFrameworkVersion("3.1+")
        self.assertIn(
            "Cannot set 'minor' with value '1+' because '+' is not allowed.",
            str(context.exception),
        )

    def test_missing_dotnet_preserves_execution_error(self):
        with tempfile.TemporaryDirectory() as directory:
            options = ServerOptions()
            options.dot_net_path = str(Path(directory, "missing-dotnet"))

            with self.assertRaises(RuntimeError) as context:
                RuntimeFrameworkVersionMatcher.get_framework_versions(options)

            self.assertEqual(
                f"Unable to execute '{options.dot_net_path}' to retrieve installed .NET runtimes. "
                "Install the required .NET runtime, set ServerOptions.dot_net_path, "
                "or use with_auto_downloaded_server() to run without system .NET.",
                str(context.exception),
            )
            self.assertIsInstance(context.exception.__cause__, OSError)

    def test_reads_required_runtime_from_server_config(self):
        with tempfile.TemporaryDirectory() as directory:
            server = Path(directory, "Raven.Server.dll")
            server.touch()
            Path(directory, "Raven.Server.runtimeconfig.json").write_text(
                '{"runtimeOptions":{"frameworks":['
                '{"name":"Microsoft.NETCore.App","version":"10.0.9"},'
                '{"name":"Microsoft.AspNetCore.App","version":"10.0.9"}'
                "]}}",
                encoding="utf-8",
            )

            self.assertEqual(
                "10.0.9+",
                RuntimeFrameworkVersionMatcher.required_framework_version(str(server)),
            )

    def get_runtimes(self):
        result = [
            RuntimeFrameworkVersion("2.1.3"),
            RuntimeFrameworkVersion("2.1.4"),
            RuntimeFrameworkVersion("2.1.11"),
            RuntimeFrameworkVersion("2.2.0"),
            RuntimeFrameworkVersion("2.2.1"),
            RuntimeFrameworkVersion("3.1.0"),
            RuntimeFrameworkVersion("3.1.1"),
            RuntimeFrameworkVersion("3.1.2"),
            RuntimeFrameworkVersion("3.1.3"),
            RuntimeFrameworkVersion("3.2.3"),
            RuntimeFrameworkVersion("5.0.0-rc.2.20475.17"),
            RuntimeFrameworkVersion("5.0.3"),
            RuntimeFrameworkVersion("5.0.4"),
            RuntimeFrameworkVersion("6.0.0-preview.6.21352.12"),
        ]

        return result
