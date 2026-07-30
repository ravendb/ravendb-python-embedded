from pathlib import Path
from unittest import TestCase

from ravendb_embedded import ServerOptions


class TestServerOptions(TestCase):
    def test_default_data_and_logs_remain_under_the_package_directory(self):
        options = ServerOptions()

        self.assertEqual(ServerOptions.BASE_MODULE_DIRECTORY + "/RavenDB", options.data_directory)
        self.assertEqual(ServerOptions.BASE_MODULE_DIRECTORY + "/RavenDB/Logs", options.logs_path)

    def test_default_logs_follow_an_explicit_data_directory(self):
        options = ServerOptions()
        options.data_directory = "custom-data"
        self.assertEqual(str(Path("custom-data", "Logs")), options.logs_path)

        options.logs_path = "custom-logs"
        options.data_directory = "other-data"
        self.assertEqual("custom-logs", options.logs_path)

    def test_instance_is_a_deprecated_constructor_alias(self):
        with self.assertWarnsRegex(
            DeprecationWarning,
            r"construct ServerOptions\(\) directly",
        ):
            options = ServerOptions.INSTANCE()

        self.assertIsInstance(options, ServerOptions)
