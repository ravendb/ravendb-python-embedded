import os
from unittest import TestCase

from ravendb_embedded.raven_server_runner import RavenServerRunner


class TestRavenServerRunner(TestCase):
    def test_parent_process_id_is_the_current_python_process(self):
        self.assertEqual(str(os.getpid()), RavenServerRunner.get_process_id())
