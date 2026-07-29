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
options.accept_eula = True  # Set only after reviewing the RavenDB EULA.
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
options.accept_eula = True
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
options.accept_eula = True
options.with_external_server("/path/to/extracted/Server")

with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store("MyDatabase") as store:
        ...
```

The native apphost is run directly, so `dotnet` is not called. Server packages are available on
the [RavenDB downloads page](https://ravendb.net/downloads).

Runnable walkthrough: [Lab 02 — external self-contained server](labs/02-embedded-external-server.md).

### Advanced server sources

`with_external_server()` also accepts a ZIP archive containing RavenDB server files. Applications
that ship the archive as a Python package resource can use
`ExtractFromPkgResourceServerProvider(package, resource_name)`. For other sources, implement
`ProvideRavenDBServer.provide(target_directory)` and assign the provider to `options.provider`.

## Configuration

Create a `ServerOptions` instance before starting the server:

Construct options with `ServerOptions()`. The misleading `ServerOptions.INSTANCE()` constructor
alias is deprecated and will be removed in a future release.

- `data_directory`: where database data is stored.
- `logs_path`: where RavenDB writes its logs.
- `accept_eula`: must be set to `True` explicitly after reviewing the RavenDB EULA.
- `server_url`: address to bind; the default uses localhost and a free port.
- `dot_net_path`: path to `dotnet` for bundled mode when it is not on `PATH`.
- `command_line_args`: additional
  [RavenDB server arguments](https://ravendb.net/docs/article-page/latest/csharp/server/configuration/command-line-arguments).
- `framework_version`: defaults to `auto`, which reads the server runtime configuration and selects
  a compatible installed .NET patch. Set an exact version for advanced setups, or `None`/`""` to
  use the dotnet host's normal roll-forward behavior.
- `graceful_shutdown_timeout`: how long to wait before terminating the child process.
- `process_kill_timeout`: how long to wait for the process after terminating or killing it.
- `max_server_startup_time_duration`: maximum server startup time.

Startup failures raise `ServerStartupError`. When the configured startup duration expires, the
more specific `ServerStartupTimeoutError` is raised. A failed start does not dispose the
`EmbeddedServer`; correct the configuration and call `start_server()` on the same instance again.

### License and EULA

The package never accepts the RavenDB EULA on your behalf. Review the
[RavenDB EULA](https://ravendb.net/legal/terms) and set `options.accept_eula = True` before
starting RavenDB.

Configure a license through `options.licensing`:

```python
options.licensing.license = '{"Id": "..."}'  # Inline license JSON
# Or:
options.licensing.license_path = "/path/to/license.json"

options.licensing.disable_auto_update = True
options.licensing.disable_auto_update_from_api = True
options.licensing.disable_license_support_check = True
options.licensing.throw_on_invalid_or_missing_license = True
```

The fail-fast option is useful in CI and production environments where falling back to an
unlicensed server would hide a configuration problem.

### HTTPS and client certificates

Use `ServerOptions.secured()` to start RavenDB over HTTPS:

```python
options = ServerOptions()
options.accept_eula = True
options.secured(
    "server.pfx",
    "client.pem",
    server_pfx_certificate_password="",
    ca_certificate_path="ca.crt",
)
```

The returned `DocumentStore` receives the client certificate and custom CA automatically.

When another process supplies the server certificate, use `secured_with_certificate_exec()`:

```python
options.secured_with_certificate_exec(
    certificate_exec="python",
    certificate_arguments='"load_certificate.py" "server.pfx"',
    client_pem_certificate_path="client.pem",
    ca_certificate_path="ca.crt",
)
```

The certificate command must write the PFX bytes to standard output.

Runnable walkthrough: [Lab 04 — secured embedded server](labs/04-embedded-secured.md).

### Server lifecycle

Use `get_server_process_id()` to inspect the child process. `stop_server()` stops RavenDB without
disposing the `EmbeddedServer`, and `restart_server()` starts it again with the same options.
Calling `close()` stops the process and disposes all document stores.

The public API is synchronous, matching the RavenDB Python client's execution model. Server start,
shutdown, and restart calls block until the requested lifecycle transition completes. Async
applications can run these blocking lifecycle calls with `asyncio.to_thread()` instead of
maintaining a second embedded API with different behavior.

`EmbeddedServer` is intentionally not a singleton. An application may run independent server
instances in the same Python process; give each instance a different `data_directory` and
`logs_path`. Prefer `with EmbeddedServer() as server:` so the context manager always closes that
instance's process and document stores.

Register a process-exit callback when the application needs to observe server failures:

```python
server.add_server_process_exited(
    lambda event: print(event.process_id, event.exit_code, event.expected)
)
```

Callbacks run on a background thread. `event.expected` is `True` for exits caused by
`stop_server()`, `restart_server()`, or `close()`, and `False` when the child exits unexpectedly.

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
