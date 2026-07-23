import platform
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from ravendb_embedded.provide import CopyServerProvider, ProvideRavenDBServer

_DOWNLOAD_BASE = "https://hibernatingrhinos.com/downloads"


def _default_version_line() -> str:
    # Match the installed package's RavenDB line (e.g. 7.2.5 -> "7.2"); fall back if unknown.
    try:
        from importlib.metadata import version

        return ".".join(version("ravendb-embedded").split(".")[:2])
    except Exception:
        return "7.2"


def _platform_download() -> tuple:
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    system = platform.system()
    if system == "Windows":
        return f"RavenDB for Windows {arch}", "zip"
    if system == "Darwin":
        return f"RavenDB for OSX {arch}", "tar.bz2"
    return f"RavenDB for Linux {arch}", "tar.bz2"


def ensure_server(version: str = None, cache_root: str = None) -> str:
    """Return a local self-contained Server directory, downloading and caching on first use.

    The download is a self-contained build (bundles its own .NET), so it runs with no system
    .NET. Pulling `latest` for the version line is intentional: a self-contained build never has
    to match anything on the host. The cache is keyed on version + platform, so later runs reuse
    it and never re-download.
    """
    version = version or _default_version_line()
    cache_root = Path(cache_root) if cache_root else Path.home() / ".cache" / "ravendb-embedded"
    label, extension = _platform_download()
    target = cache_root / version / label.replace(" ", "_")

    cached = next(target.rglob("Raven.Server.dll"), None) if target.is_dir() else None
    if cached:
        return str(cached.parent)

    target.mkdir(parents=True, exist_ok=True)
    url = f"{_DOWNLOAD_BASE}/{label.replace(' ', '%20')}/latest?version={version}"
    archive = target / f"ravendb.{extension}"
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


class OnDemandServerProvider(ProvideRavenDBServer):
    """Download (once) and cache a self-contained server, then run it with no system .NET.

    The self-contained build bundles its own runtime, so the server runs via its native apphost;
    `dot_net_path` is never used. The download happens on first `start_server()` and is cached.
    """

    def __init__(self, version: str = None, cache_root: str = None):
        self.version = version
        self.cache_root = cache_root
        self.is_single_file_app = True

    def provide(self, target_directory: str) -> None:
        CopyServerProvider(ensure_server(self.version, self.cache_root)).provide(target_directory)
