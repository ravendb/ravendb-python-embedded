import io
import tarfile
import tempfile
import threading
import time
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ravendb_embedded import on_demand
from ravendb_embedded.on_demand import _extract_safely, _platform_download, _platform_download_for, ensure_server


def _server_archive(extension):
    archive = io.BytesIO()
    payload = b"real cache payload" * 4096
    path = "RavenDB/Server/Raven.Server.dll"

    if extension == "zip":
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr(path, payload)
    else:
        with tarfile.open(fileobj=archive, mode="w:bz2") as bundle:
            member = tarfile.TarInfo(path)
            member.size = len(payload)
            bundle.addfile(member, io.BytesIO(payload))

    return archive.getvalue()


@contextmanager
def _serve_archive(payload, interrupt=False, pause=False):
    class ArchiveHandler(BaseHTTPRequestHandler):
        request_count = 0
        request_count_lock = threading.Lock()

        def do_GET(self):
            with self.request_count_lock:
                type(self).request_count += 1

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()

            midpoint = max(1, len(payload) // 2)
            self.wfile.write(payload[:midpoint])
            self.wfile.flush()
            if interrupt:
                self.close_connection = True
                return
            if pause:
                time.sleep(0.1)
            self.wfile.write(payload[midpoint:])

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), ArchiveHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", ArchiveHandler
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join()


@contextmanager
def _download_from(base_url):
    original = on_demand._DOWNLOAD_BASE
    on_demand._DOWNLOAD_BASE = base_url
    try:
        yield
    finally:
        on_demand._DOWNLOAD_BASE = original


class TestOnDemand(unittest.TestCase):
    def test_cache_hit_skips_download(self):
        # A populated cache must be reused without any network call.
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

    def test_interrupted_download_does_not_poison_cache(self):
        label, extension = _platform_download()
        payload = _server_archive(extension)

        with tempfile.TemporaryDirectory() as cache_root:
            target = Path(cache_root, "interrupted", label.replace(" ", "_"))

            with _serve_archive(payload, interrupt=True) as (base_url, _):
                with _download_from(base_url):
                    with self.assertRaises((tarfile.ReadError, zipfile.BadZipFile)):
                        ensure_server(version="interrupted", cache_root=cache_root)

            self.assertFalse(target.exists())
            self.assertEqual([], list(target.parent.glob("download-*")))

            with _serve_archive(payload) as (base_url, _):
                with _download_from(base_url):
                    resolved = Path(ensure_server(version="interrupted", cache_root=cache_root))

            self.assertEqual(target / "RavenDB" / "Server", resolved)
            self.assertTrue((resolved / "Raven.Server.dll").is_file())

    def test_concurrent_first_downloads_leave_one_complete_cache(self):
        label, extension = _platform_download()
        payload = _server_archive(extension)
        workers = 4
        start = threading.Barrier(workers)

        with tempfile.TemporaryDirectory() as cache_root:
            with _serve_archive(payload, pause=True) as (base_url, handler):
                with _download_from(base_url):

                    def resolve():
                        start.wait()
                        return ensure_server(version="concurrent", cache_root=cache_root)

                    with ThreadPoolExecutor(max_workers=workers) as executor:
                        resolved = list(executor.map(lambda _: resolve(), range(workers)))

            target = Path(cache_root, "concurrent", label.replace(" ", "_"))
            expected = target / "RavenDB" / "Server"
            self.assertEqual([str(expected)] * workers, resolved)
            self.assertTrue((expected / "Raven.Server.dll").is_file())
            self.assertGreaterEqual(handler.request_count, 2)
            self.assertEqual([], list(target.parent.glob("download-*")))
