# ravendb-embedded

`ravendb-embedded` starts a real RavenDB server as a child process of your Python application.
The server starts with your code, stops with it, and is accessed through the standard `ravendb`
client.

Use it for local development, integration tests, or applications that should manage their own
RavenDB process.

## Install

```bash
pip install ravendb-embedded
```

Python 3.10+ is required.

## Quick start

The default mode uses the RavenDB binaries included in the wheel and a compatible system .NET
runtime:

```python
from ravendb_embedded import EmbeddedServer, ServerOptions

options = ServerOptions()
options.data_directory = "./data/RavenDB"
options.logs_path = "./logs/RavenDB"

with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store("MyDatabase") as store:
        with store.open_session() as session:
            session.store({"name": "Ayende"}, "people/1")
            session.save_changes()
```

## Choose how RavenDB runs

| Mode | System .NET required? | Server lifecycle | Best for |
|------|-----------------------|------------------|----------|
| [Bundled server](#bundled-server-default) | Yes | Managed by the package | The simplest local setup |
| [On-demand self-contained server](#on-demand-self-contained-server) | No | Downloaded, cached, and managed by the package | Portable developer and CI environments |
| [Self-contained server you provide](#self-contained-server-you-provide) | No | Managed by the package | Offline or centrally controlled server artifacts |

Only the bundled-server mode requires .NET to be installed on the machine running Python.

### Bundled server (default)

The wheel includes a framework-dependent RavenDB server. Its runtime requirement follows the
RavenDB version:

| `ravendb-embedded` version | Required runtime |
|----------------------------|------------------|
| 7.2.x                      | .NET 10          |
| 7.1.x                      | .NET 8           |

Run `dotnet --list-runtimes` and look for `Microsoft.NETCore.App`. Re-check this requirement when
upgrading to a new RavenDB minor version.

Runnable walkthrough: [Lab 01 — embedded zero-config](labs/01-embedded-zero-config.md).

### On-demand self-contained server

For the same managed experience without installing .NET, let the package download a
self-contained RavenDB build:

```python
from ravendb_embedded import EmbeddedServer, ServerOptions

options = ServerOptions()
options.with_auto_downloaded_server()
options.data_directory = "./data/RavenDB"
options.logs_path = "./logs/RavenDB"

with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store("MyDatabase") as store:
        ...
```

The operating system and architecture are detected at runtime, so the same Python configuration
is portable across:

- Windows x64 and x86
- Linux x64 and ARM64
- macOS x64 and ARM64

Unsupported targets, including Windows ARM64, fail with an explicit error instead of downloading
an incompatible build.

The first run downloads a self-contained server (100 MB+) and caches it under
`~/.cache/ravendb-embedded`. Later runs reuse that cache. Pass `cache_root` to
`with_auto_downloaded_server()` when you want a different location:

```python
options.with_auto_downloaded_server(cache_root="./.ravendb-cache")
```

By default, the download follows the installed package's RavenDB version line. The cache is not
refreshed automatically; remove that version's cache directory when you intentionally want to
resolve a newer server build from the same line.

The wheel does not contain a self-contained build for every platform; it downloads only the build
needed by the current machine. Self-contained mode removes the system .NET requirement, but normal
RavenDB operating-system dependencies still apply. Minimal Linux images may need their
distribution's ICU package.

Runnable walkthrough: [Lab 03 — on-demand server](labs/03-on-demand-server.md).

### Self-contained server you provide

Download and extract the Server package for the target platform, then point the package at its
`Server` directory:

```python
from ravendb_embedded import EmbeddedServer, ServerOptions

options = ServerOptions()
options.with_external_server("/path/to/extracted/Server")

with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store("MyDatabase") as store:
        ...
```

The native apphost is run directly, so `dotnet` is not called. Server packages are available on
the [RavenDB downloads page](https://ravendb.net/downloads).

Runnable walkthrough: [Lab 02 — external self-contained server](labs/02-embedded-external-server.md).

## Configuration

Create a `ServerOptions` instance before starting the server:

- `data_directory`: where database data is stored.
- `logs_path`: where RavenDB writes its logs.
- `server_url`: address to bind; the default uses localhost and a free port.
- `dot_net_path`: path to `dotnet` for bundled mode when it is not on `PATH`.
- `command_line_args`: additional
  [RavenDB server arguments](https://ravendb.net/docs/article-page/latest/csharp/server/configuration/command-line-arguments).
- `framework_version`: an exact .NET runtime version for advanced bundled-server setups.
- `graceful_shutdown_timeout`: how long to wait before terminating the child process.
- `process_kill_timeout`: how long to wait for the process after terminating or killing it.
- `max_server_startup_time_duration`: maximum server startup time.

### HTTPS and client certificates

Use `ServerOptions.secured()` to start RavenDB over HTTPS:

```python
options = ServerOptions()
options.secured(
    "server.pfx",
    "client.pem",
    server_pfx_certificate_password="",
    ca_certificate_path="ca.crt",
)
```

The returned `DocumentStore` receives the client certificate and custom CA automatically.

Runnable walkthrough: [Lab 04 — secured embedded server](labs/04-embedded-secured.md).

### Persistent data

Set `data_directory` to a stable path when data should survive process restarts. Use a temporary
directory for disposable tests.

Runnable walkthrough: [Lab 05 — persistent data](labs/05-embedded-persistent.md).

### Document stores

`get_document_store(database_name)` returns a standard RavenDB `DocumentStore` and creates the
database when needed. For finer control, create `DatabaseOptions` with
`DatabaseOptions.from_database_name()` and call `get_document_store_from_options()`.

Set `skip_creating_database=True` on `DatabaseOptions` when the database is managed elsewhere.
Call `open_studio_in_browser()` to open RavenDB Studio.

## Labs

The repository contains runnable, self-checking examples:

| Lab | Scenario | Needs system .NET? |
|-----|----------|--------------------|
| [01](labs/01-embedded-zero-config.md) | Bundled zero-config server | Yes |
| [02](labs/02-embedded-external-server.md) | Self-contained server you provide | No |
| [03](labs/03-on-demand-server.md) | Automatic platform detection, download, and cache | No |
| [04](labs/04-embedded-secured.md) | HTTPS and client-certificate authentication | Yes |
| [05](labs/05-embedded-persistent.md) | Data that survives server restarts | Yes |

The scripts live in the repository rather than the installed wheel. Clone or download the
repository, install the package, and run them from the repository root. See the
[complete labs guide](labs/README.md).

## Links

- [PyPI](https://pypi.org/project/ravendb-embedded/)
- [Source](https://github.com/ravendb/ravendb-python-embedded)
- [RavenDB Python client documentation](https://ravendb.net/docs/article-page/latest/python)
