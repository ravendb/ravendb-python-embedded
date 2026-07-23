"""Lab 04 (exploration): on-demand, cached self-contained server download.

A Playwright-style acquisition prototype: fetch a self-contained RavenDB server for the current
platform on first use, cache it, and reuse the cached copy next time (no re-download, no .NET).
This is exploratory and is NOT wired into the package default; it shows how a future
"just works, no .NET" acquisition path could look.

Run:  python labs/on_demand_server.py
"""

import platform
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

RAVENDB_VERSION = "7.2"


def _platform_download():
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    system = platform.system()
    if system == "Windows":
        return f"RavenDB for Windows {arch}", "zip"
    if system == "Darwin":
        return f"RavenDB for OSX {arch}", "tar.bz2"
    return f"RavenDB for Linux {arch}", "tar.bz2"


def ensure_server(version=RAVENDB_VERSION, cache_root=None):
    """Return a local self-contained Server directory, downloading and caching on first use."""
    cache_root = Path(cache_root) if cache_root else Path.home() / ".cache" / "ravendb-embedded"
    label, extension = _platform_download()
    target = cache_root / version / label.replace(" ", "_")

    cached = next(target.rglob("Raven.Server.dll"), None) if target.is_dir() else None
    if cached:  # cache hit: never download again ("by design")
        return str(cached.parent)

    target.mkdir(parents=True, exist_ok=True)
    url = f"https://hibernatingrhinos.com/downloads/{label.replace(' ', '%20')}/latest?version={version}"
    archive = target / f"ravendb.{extension}"
    print(f"downloading {url}")
    urllib.request.urlretrieve(url, archive)
    if extension == "zip":
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(target)
    else:
        with tarfile.open(archive) as bundle:
            bundle.extractall(target)
    archive.unlink()

    server = next(target.rglob("Raven.Server.dll"), None)
    if not server:
        raise RuntimeError(f"Server binaries not found under {target}")
    return str(server.parent)


def main():
    from ravendb_embedded import EmbeddedServer, ServerOptions

    server_dir = ensure_server()
    print("server ready at", server_dir)

    with tempfile.TemporaryDirectory() as work:
        options = ServerOptions()
        options.target_server_location = str(Path(work, "server"))
        options.data_directory = str(Path(work, "data"))
        options.logs_path = str(Path(work, "logs"))
        options.dot_net_path = "__no_dotnet__"  # proves the cached build needs no system .NET
        options.with_external_server(server_dir)
        with EmbeddedServer() as server:
            server.start_server(options)
            with server.get_document_store("Lab") as store:
                with store.open_session() as session:
                    session.store({"name": "on-demand"}, "people/1")
                    session.save_changes()

    print("Lab 04 OK: downloaded + cached a self-contained server and ran it with no system .NET.")


if __name__ == "__main__":
    main()
