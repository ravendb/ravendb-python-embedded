import io
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from ravendb_embedded.on_demand import _extract_safely, _platform_download, _platform_download_for, ensure_server


class TestOnDemand(unittest.TestCase):
    def test_cache_hit_skips_download(self):
        # A populated cache must be reused without any network call ("by design").
        with tempfile.TemporaryDirectory() as cache_root:
            label, _ = _platform_download()
            server_dir = Path(cache_root, "7.2", label.replace(" ", "_"), "Server")
            server_dir.mkdir(parents=True)
            (server_dir / "Raven.Server.dll").write_bytes(b"stub")

            resolved = ensure_server(version="7.2", cache_root=cache_root)

            self.assertEqual(str(server_dir), resolved)

    def test_platform_download_maps_supported_targets(self):
        cases = [
            ("Windows", "AMD64", ("RavenDB for Windows x64", "zip")),
            ("Windows", "x86", ("RavenDB for Windows x86", "zip")),
            ("Linux", "x86_64", ("RavenDB for Linux x64", "tar.bz2")),
            ("Linux", "aarch64", ("RavenDB for Linux arm64", "tar.bz2")),
            ("Darwin", "x86_64", ("RavenDB for MacOS x64", "tar.bz2")),
            ("Darwin", "arm64", ("RavenDB for MacOS arm64", "tar.bz2")),
        ]

        for system, machine, expected in cases:
            with self.subTest(system=system, machine=machine):
                self.assertEqual(expected, _platform_download_for(system, machine))

    def test_platform_download_rejects_unavailable_targets(self):
        cases = [
            ("Windows", "arm64"),
            ("Linux", "i686"),
            ("Darwin", "i386"),
            ("FreeBSD", "x86_64"),
            ("Linux", "mips"),
        ]

        for system, machine in cases:
            with self.subTest(system=system, machine=machine):
                with self.assertRaises(RuntimeError):
                    _platform_download_for(system, machine)

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
