from unittest import TestCase

from ravendb_embedded.options import ServerOptions
from ravendb_embedded.runtime_framework_version_matcher import RuntimeFrameworkVersionMatcher, RuntimeFrameworkVersion


class TestRuntimeFrameworkVersionMatcher(TestCase):
    def test_match_1(self):
        options = ServerOptions()
        default_framework_version = ServerOptions.INSTANCE().framework_version

        self.assertIn(RuntimeFrameworkVersionMatcher.GREATER_OR_EQUAL, default_framework_version)

        options.framework_version = None
        self.assertIsNone(RuntimeFrameworkVersionMatcher.match(options))

        options = ServerOptions()
        framework_version = RuntimeFrameworkVersion(options.framework_version)
        framework_version.patch = None

        options.framework_version = framework_version.__str__()
        match = RuntimeFrameworkVersionMatcher.match(options)
        self.assertIsNotNone(match)

        match_framework_version = RuntimeFrameworkVersion(match)
        self.assertIsNotNone(match_framework_version.major)
        self.assertIsNotNone(match_framework_version.minor)
        self.assertIsNotNone(match_framework_version.patch)

        self.assertTrue(framework_version.match(match_framework_version))

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
        self.assertEqual(RuntimeFrameworkVersionMatcher.match_runtime(runtime, runtimes), "5.0.0-rc.2.20475.17")

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
        self.assertIn("Could not find a matching runtime for '3.1.4+'. Available runtimes:", str(context.exception))

        with self.assertRaises(RuntimeError) as context:
            RuntimeFrameworkVersion("6.0.0+-preview.6.21352.12")
        self.assertIn(
            "Cannot set 'patch' with value '0+' because '+' is not allowed when suffix ('preview.6.21352.12') is set",
            str(context.exception),
        )

        with self.assertRaises(RuntimeError) as context:
            RuntimeFrameworkVersion("6+")
        self.assertIn("Cannot set 'major' with value '6+' because '+' is not allowed.", str(context.exception))

        with self.assertRaises(RuntimeError) as context:
            RuntimeFrameworkVersion("3.1+")
        self.assertIn("Cannot set 'minor' with value '1+' because '+' is not allowed.", str(context.exception))

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
