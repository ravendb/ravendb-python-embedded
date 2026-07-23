import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ravendb_embedded.on_demand import ensure_server, _platform_download


class TestOnDemand(unittest.TestCase):
    def test_cache_hit_skips_download(self):
        # A populated cache must be reused without any network call ("by design").
        with tempfile.TemporaryDirectory() as cache_root:
            label, _ = _platform_download()
            server_dir = Path(cache_root, "7.2", label.replace(" ", "_"), "Server")
            server_dir.mkdir(parents=True)
            (server_dir / "Raven.Server.dll").write_bytes(b"stub")

            with mock.patch("urllib.request.urlretrieve", side_effect=AssertionError("cache hit must not download")):
                resolved = ensure_server(version="7.2", cache_root=cache_root)

            self.assertEqual(str(server_dir), resolved)

    def test_platform_download_targets_a_known_os(self):
        label, extension = _platform_download()
        self.assertTrue(label.startswith("RavenDB for "))
        self.assertIn(extension, ("zip", "tar.bz2"))
