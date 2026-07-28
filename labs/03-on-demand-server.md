# Lab 03: On-demand, cached self-contained server (no .NET)

**For:** the no-.NET experience of Lab 02 without downloading and extracting a server yourself.
Call `with_auto_downloaded_server()`; on first use the driver fetches a self-contained build for this
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
options.with_auto_downloaded_server()   # download + cache a self-contained server on first use

with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store("Lab") as store:
        ...  # ordinary RavenDB client code, with no .NET on the machine
```

`with_auto_downloaded_server(version=None, cache_root=None)` defaults the version to the installed
package's RavenDB line and caches under `~/.cache/ravendb-embedded`. Pass `cache_root` to point
it at a directory your CI restores between runs.

## Version and host requirements

The package fetches the latest self-contained build for the installed RavenDB version line. Its
bundled runtime removes the host .NET compatibility matrix, and the cache keeps later runs on the
same downloaded build.

Automatic downloads support Windows x64/x86, Linux x64/ARM64, and macOS x64/ARM64. Unsupported
targets fail with an explicit message instead of downloading a build for the wrong architecture.

Normal RavenDB operating-system dependencies still apply. Standard Linux distributions and hosted
CI images usually include them; minimal Linux images may need their distribution's ICU package.

## Cost to know about

The first use downloads a self-contained build (100 MB+) and the cache keeps it on disk. Every
run after that is offline and instant. If disk or first-run latency matters, prefer Lab 02 (you
provide the server) or Lab 01 (bundled server, needs .NET).

The cache is not refreshed automatically. To pick up a newer build from the same RavenDB line,
remove that line's cache directory or use a new `cache_root`.

## Takeaway

`with_auto_downloaded_server()` gives the no-.NET path of Lab 02 without a manual server download:
one call, then ordinary client code.
