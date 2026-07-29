from unittest import TestCase

from ravendb_embedded import ServerOptions


class TestServerOptions(TestCase):
    def test_instance_is_a_deprecated_constructor_alias(self):
        with self.assertWarnsRegex(
            DeprecationWarning,
            r"construct ServerOptions\(\) directly",
        ):
            options = ServerOptions.INSTANCE()

        self.assertIsInstance(options, ServerOptions)
