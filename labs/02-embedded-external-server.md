# Lab 02: External self-contained server (no system .NET)

**For:** machines or CI that do not have .NET installed. You bring a **self-contained**
RavenDB server (it bundles the .NET runtime); the driver runs its native apphost directly and
never calls `dotnet`.

## Get a self-contained server

Download and extract a server build from ravendb.net (one per platform), for example:

- Linux x64: `https://hibernatingrhinos.com/downloads/RavenDB%20for%20Linux%20x64/latest?version=7.2`
- Windows x64: `https://hibernatingrhinos.com/downloads/RavenDB%20for%20Windows%20x64/latest?version=7.2`

The server files live in the `Server/` subfolder of the extracted archive.

## Run it

```bash
pip install ravendb-embedded
RAVENDB_SELF_CONTAINED_SERVER=/path/to/extracted/Server python labs/02_embedded_external_server.py
```

The complete example is [`02_embedded_external_server.py`](02_embedded_external_server.py).
The core is:

```python
from ravendb_embedded import EmbeddedServer, ServerOptions

options = ServerOptions()
options.with_external_server("/path/to/extracted/Server")  # a self-contained build
with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store("Lab") as store:
        ...  # ordinary RavenDB client code, with no .NET on the machine
```

## How it decides not to use `dotnet`

`ExternalServerProvider` reads `Raven.Server.runtimeconfig.json`. A self-contained build lists
`includedFrameworks` (its bundled runtime), so the driver marks it "run the native apphost"
and launches `Raven.Server` (or `Raven.Server.exe` on Windows) directly, with **no `dotnet`**.
A framework-dependent build (only a `framework` reference, no bundled runtime) still runs via
`dotnet Raven.Server.dll` and needs a system .NET, which is Lab 01.

## Takeaway

No .NET on the box, at the cost of fetching and caching the server build yourself. If you would
rather not manage a server at all, run one in a container and attach to it: Lab 03.
