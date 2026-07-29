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
from ravendb_embedded import EmbeddedServer, ServerOptions

options = ServerOptions()
options.accept_eula = True

with EmbeddedServer() as server:
    server.start_server(options)
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
3. `ServerOptions.framework_version` defaults to `auto`. The package reads the bundled
   `Raven.Server.runtimeconfig.json`, finds the required .NET line, and selects a compatible
   installed patch. The host does **not** roll forward across major versions, which is why a
   net10.0 server still requires .NET 10.
4. The one exception: point the server at a **self-contained** build (an apphost
   `Raven.Server` with the runtime bundled) and it runs **without `dotnet`**. That is Lab 02.

## Takeaway

This is the most convenient path, but it buys a hard dependency on a system-wide .NET in a
specific major version. If you would rather not manage .NET, use Lab 02 (a self-contained server
you provide) or Lab 03 (one the package downloads and caches). To run RavenDB separately in Docker
and give each test an isolated database, use the testdriver's
[attach lab](https://github.com/ravendb/ravendb-python-testdriver/blob/v7.2/labs/01-attach-to-server.md).
