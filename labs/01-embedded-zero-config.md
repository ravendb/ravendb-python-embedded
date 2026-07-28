# Lab 01: Embedded, zero-config

**For:** local development or CI on a machine that already has .NET installed. You want
`pip install ravendb-embedded` and a working RavenDB server with nothing set up on the side.

**Requirement:** RavenDB 7.2.x needs **.NET 10** (7.1.x needed .NET 8). Verify with
`dotnet --list-runtimes` and look for `Microsoft.NETCore.App 10.0.x`.

## Run it

```bash
pip install ravendb-embedded
python labs/01_embedded_zero_config.py
```

The complete, runnable example is [`01_embedded_zero_config.py`](01_embedded_zero_config.py).
The core is just:

```python
from ravendb_embedded import EmbeddedServer

with EmbeddedServer() as server:
    server.start_server()
    with server.get_document_store("Lab") as store:
        with store.open_session() as session:
            session.store({"name": "Ayende"}, "people/1")
            session.save_changes()
```

## How the .NET runtime is picked (under the hood)

1. The default provider (`CopyServerFromNugetProvider`) unpacks the **framework-dependent**
   server (`Raven.Server.dll`) that ships inside the wheel.
2. `RavenServerRunner` launches it as **`dotnet Raven.Server.dll ...`**, using the `dotnet`
   found on your `PATH` (`ServerOptions.dot_net_path`).
3. `ServerOptions.framework_version` is empty by default, so no `--fx-version` is passed and
   standard .NET host resolution applies. The host does **not** roll forward across major
   versions, which is why a net10.0 server hard-fails on a machine that only has .NET 8
   (error: "You must install ... version 10.0.x").
4. The one exception: point the server at a **self-contained** build (an apphost
   `Raven.Server` with the runtime bundled) and it runs **without `dotnet`**. That is Lab 02.

## Takeaway

This is the most convenient path, but it buys a hard dependency on a system-wide .NET in a
specific major version. If you would rather not manage .NET, use Lab 02 (external
self-contained server) or Lab 03 (attach to a server you run yourself, e.g. via Docker).
