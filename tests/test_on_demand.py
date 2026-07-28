import io
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from ravendb_embedded.on_demand import _extract_safely, _platform_download, ensure_server


class TestOnDemand(unittest.TestCase):
    def test_cache_hit_skips_download(self):
        # A populated cache must be reused without any network call ("by design").
        with tempfile.TemporaryDirectory() as cache_root:
            label, _ = _platform_download()
            server_dir = Path(cache_root, "7.2", label.replace(" ", "_"), "Server")
            server_dir.mkdir(parents=True)
            (server_dir / "Raven.Server.dll").write_bytes(b"stub")

            with mock.patch("urllib.request.urlopen", side_effect=AssertionError("cache hit must not download")):
                resolved = ensure_server(version="7.2", cache_root=cache_root)

            self.assertEqual(str(server_dir), resolved)

    def test_platform_download_targets_a_known_os(self):
        label, extension = _platform_download()
        self.assertTrue(label.startswith("RavenDB for "))
        self.assertIn(extension, ("zip", "tar.bz2"))

    def test_extract_rejects_path_traversal(self):
        # A tampered archive must not be able to write outside the destination (zip/tar slip).
        with tempfile.TemporaryDirectory() as work:
            dest = Path(work, "out")
            dest.mkdir()

            bad_tar = Path(work, "bad.tar.bz2")
            with tarfile.open(bad_tar, "w:bz2") as tar:
                payload = b"x"
                info = tarfile.TarInfo("../escaped.txt")
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
            with self.assertRaises(RuntimeError):
                _extract_safely(bad_tar, dest, "tar.bz2")

            bad_zip = Path(work, "bad.zip")
            with zipfile.ZipFile(bad_zip, "w") as archive:
                archive.writestr("../escaped.txt", "x")
            with self.assertRaises(RuntimeError):
                _extract_safely(bad_zip, dest, "zip")

            self.assertFalse((Path(work) / "escaped.txt").exists())
