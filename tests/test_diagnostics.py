import logging
from unittest import TestCase

from ravendb_embedded import EmbeddedServer


class TestDiagnostics(TestCase):
    def test_studio_url_disables_analytics(self):
        self.assertEqual(
            "http://127.0.0.1:8080/studio/index.html?disableAnalytics=true",
            EmbeddedServer._get_studio_url("http://127.0.0.1:8080/"),
        )

    def test_embedded_logging_uses_python_logging_hierarchy(self):
        server = EmbeddedServer()

        with self.assertLogs("ravendb_embedded.EmbeddedServer", logging.DEBUG) as captured:
            server._log_debug("embedded diagnostic")

        self.assertEqual("ravendb_embedded.EmbeddedServer", server.logger.name)
        self.assertIn("embedded diagnostic", captured.output[0])
