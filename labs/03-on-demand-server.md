# Lab 03: On-demand, cached self-contained server (exploration)

**Status:** exploration. This is NOT wired into the package default. It shows how a future
"just works, no .NET" acquisition path could look, in the spirit of how Playwright fetches its
browsers on first use.

**For:** anyone who wants Lab 02 (no system .NET) without manually downloading and extracting a
server. The helper fetches a self-contained build for the current platform on first use, caches
it, and reuses the cached copy every time after that.

## The idea

Lab 02 needs a self-contained `Server/` folder that you download and extract yourself. This lab
automates that one step:

1. On first use, download the self-contained build for this OS and architecture.
2. Extract it into a cache directory and remember it.
3. On every later run, reuse the cached copy: no re-download, no `dotnet`.

## Run it

```bash
pip install ravendb-embedded
python labs/on_demand_server.py
```

The complete example is [`on_demand_server.py`](on_demand_server.py). The core is:

```python
from ravendb_embedded import EmbeddedServer, ServerOptions
from on_demand_server import ensure_server

server_dir = ensure_server()          # download+cache on first use, cache hit afterwards
options = ServerOptions()
options.with_external_server(server_dir)   # a self-contained build, so no dotnet
with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store("Lab") as store:
        ...  # ordinary RavenDB client code, with no .NET on the machine
```

## Caching, by design

`ensure_server()` keys the cache on version + platform label and looks for
`Raven.Server.dll` under the cache directory. If it is present the download step is skipped
entirely, so the second run (and every run after) is offline and instant. The default cache
root is `~/.cache/ravendb-embedded`; pass `cache_root=...` to override it (the CI-style pattern
is to point it at a directory the CI cache restores between runs).

Because the downloaded build is self-contained, the run path is identical to Lab 02:
`ExternalServerProvider` sees `includedFrameworks` in the runtime config, runs the native
apphost (`Raven.Server.exe` on Windows, `Raven.Server` elsewhere), and never calls `dotnet`.

## Why pulling `latest` is fine (on purpose)

Fetching the `latest` self-contained build for the version line is deliberate. A self-contained
build bundles its own .NET runtime, so it does not have to match anything on the host: whatever
`latest` returns is a server that just runs. There is no host .NET compatibility matrix to pin
against, which is exactly what makes "grab latest and run" safe here (a framework-dependent build
could not make that promise). The cache then freezes whatever you first pulled, so later runs stay
stable without any extra pinning.

## Why it is still only an exploration

- A self-contained build is large (100 MB+), so the first-use download and the on-disk cache
  footprint are real costs.
- Making this the default changes the install story (a network fetch on first use) and needs a
  decision on where the cache lives, how big it may grow, and when it is invalidated.

## Takeaway

The acquisition step from Lab 02 can be automated and cached, giving a no-.NET experience with no
manual download. The mechanism works (this lab runs it); making it the package default is a
product decision about the install story and cache policy, not a code gap.
