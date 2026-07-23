# Lab 03: On-demand, cached self-contained server (no .NET)

**For:** the no-.NET experience of Lab 02 without downloading and extracting a server yourself.
Call `with_on_demand_server()`; on first use the driver fetches a self-contained build for this
platform, caches it, and reuses the cache from then on. A self-contained build bundles its own
runtime, so the server runs its native apphost and never calls `dotnet`.

## Run it

```bash
pip install ravendb-embedded
python labs/03_on_demand_server.py
```

The complete example is [`03_on_demand_server.py`](03_on_demand_server.py). The core is:

```python
from ravendb_embedded import EmbeddedServer, ServerOptions

options = ServerOptions()
options.with_on_demand_server()   # download + cache a self-contained server on first use

with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store("Lab") as store:
        ...  # ordinary RavenDB client code, with no .NET on the machine
```

`with_on_demand_server(version=None, cache_root=None)` defaults the version to the installed
package's RavenDB line and caches under `~/.cache/ravendb-embedded`. Pass `cache_root` to point
it at a directory your CI restores between runs.

## Why pulling `latest` is fine (on purpose)

Fetching the `latest` self-contained build for the version line is deliberate. A self-contained
build bundles its own .NET runtime, so it does not have to match anything on the host: whatever
`latest` returns is a server that just runs. There is no host .NET compatibility matrix to pin
against, which is exactly what makes "grab latest and run" safe here (a framework-dependent build
could not make that promise). The cache then freezes whatever you first pulled, so later runs stay
stable without any extra pinning.

## Cost to know about

The first use downloads a self-contained build (100 MB+) and the cache keeps it on disk. Every
run after that is offline and instant. If disk or first-run latency matters, prefer Lab 02 (you
provide the server) or Lab 01 (bundled server, needs .NET).

## Takeaway

`with_on_demand_server()` gives the no-.NET path of Lab 02 with zero manual steps: one call, then
ordinary client code.
