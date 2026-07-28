import os
import platform
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

_DOWNLOAD_BASE = "https://hibernatingrhinos.com/downloads"
_DOWNLOAD_TIMEOUT_SECONDS = 30


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


def _extract_safely(archive: Path, dest: Path, extension: str) -> None:
    # Guard against archive path-traversal (zip/tar slip): every member must resolve inside dest,
    # and tar links are refused. (The stdlib default extraction is unfiltered before Python 3.12.)
    dest = dest.resolve()

    def _inside(name: str) -> bool:
        return (dest / name).resolve() == dest or dest in (dest / name).resolve().parents

    if extension == "zip":
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if not _inside(name):
                    raise RuntimeError(f"Refusing to extract unsafe archive path: {name}")
            bundle.extractall(dest)
    else:
        with tarfile.open(archive) as bundle:
            for member in bundle.getmembers():
                if member.issym() or member.islnk():
                    raise RuntimeError(f"Refusing to extract a link member from archive: {member.name}")
                if not _inside(member.name):
                    raise RuntimeError(f"Refusing to extract unsafe archive path: {member.name}")
            bundle.extractall(dest)


def ensure_server(version: str = None, cache_root: str = None) -> str:
    """Return a local self-contained Server directory, downloading and caching on first use.

    The download is a self-contained build (bundles its own .NET), so it runs with no system
    .NET. Pulling `latest` for the version line is intentional: a self-contained build never has
    to match anything on the host. A completed cache entry (keyed on version + platform) is reused
    and never re-downloaded. Download and extraction happen in a private temp directory that is
    moved into place only once complete, so an interrupted or concurrent first run never leaves a
    half-populated cache.
    """
    version = version or _default_version_line()
    root = Path(cache_root) if cache_root else Path.home() / ".cache" / "ravendb-embedded"
    label, extension = _platform_download()
    line_dir = root / version
    target = line_dir / label.replace(" ", "_")

    cached = next(target.rglob("Raven.Server.dll"), None) if target.is_dir() else None
    if cached:
        return str(cached.parent)

    line_dir.mkdir(parents=True, exist_ok=True)
    url = f"{_DOWNLOAD_BASE}/{label.replace(' ', '%20')}/latest?version={version}"
    work = Path(tempfile.mkdtemp(prefix="download-", dir=line_dir))
    try:
        archive = work / f"ravendb.{extension}"
        try:
            with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response, open(archive, "wb") as out:
                shutil.copyfileobj(response, out)
        except OSError as error:
            raise RuntimeError(f"Failed to download a self-contained RavenDB server from {url}: {error}") from error

        extracted = work / "server"
        extracted.mkdir()
        _extract_safely(archive, extracted, extension)
        if not next(extracted.rglob("Raven.Server.dll"), None):
            raise RuntimeError(f"Downloaded archive did not contain a RavenDB server: {url}")

        try:
            os.replace(extracted, target)  # atomic on the same filesystem
        except OSError:
            # A concurrent first run may have populated the cache first; prefer a complete entry.
            if not next(target.rglob("Raven.Server.dll"), None):
                shutil.rmtree(target, ignore_errors=True)
                os.replace(extracted, target)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    server = next(target.rglob("Raven.Server.dll"), None)
    if not server:
        raise RuntimeError(f"Server binaries not found under {target}")
    return str(server.parent)
