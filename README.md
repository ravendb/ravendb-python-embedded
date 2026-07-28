# ravendb-embedded

`ravendb-embedded` runs a real RavenDB server from inside your Python program. You `pip install`
it, start the server in-process, and talk to it with the normal `ravendb` client. There is no
separate server to install, configure, or keep running: the server's lifetime follows your
process.

Reach for it when you want:

- **Local development** without setting up a standalone RavenDB.
- **Integration tests** against a real server instead of a mock (see also `ravendb-test-driver`).
- **Small or self-contained apps** that ship the database alongside the code.

```python
from ravendb_embedded import EmbeddedServer

with EmbeddedServer() as server:
    server.start_server()
    with server.get_document_store("Embedded") as store:
        with store.open_session() as session:
            session.store({"name": "Ayende"}, "people/1")
            session.save_changes()
```

## Installation

```bash
pip install ravendb-embedded
```

The install includes a copy of the RavenDB server binaries. Python 3.10+ is required.

## The .NET requirement (read this)

The bundled server is a .NET application, so a matching **.NET runtime** must be on the machine.
The required version tracks the bundled server:

| `ravendb-embedded` version | Required runtime |
|----------------------------|------------------|
| 7.2.x                      | .NET 10          |
| 7.1.x                      | .NET 8           |

Check what is installed with `dotnet --list-runtimes` (look for `Microsoft.NETCore.App`). Because
the requirement follows the bundled server, it can change on a minor upgrade, so re-check it when
you bump versions.

If the machine cannot or should not have .NET, use the self-contained path under
[Run without installing .NET](#run-without-installing-net) below.

## Usage

The three sections below are the ways people actually use this package. Pick the one that matches
your environment; each links to a runnable walkthrough in `labs/`.

### Run it (the default, needs .NET)

Start the server and get a document store. This is the zero-config path and uses the system .NET
described above. Pass a `ServerOptions` when you want to control where data lives, the bind URL,
and so on.

```python
from ravendb_embedded import EmbeddedServer, ServerOptions

options = ServerOptions()
options.data_directory = "MYPATH/RavenDBDataDir"   # optional; defaults to a local RavenDB folder

with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store("MyDb") as store:
        ...   # ordinary ravendb client code
```

Runnable walkthrough: [`labs/01-embedded-zero-config.md`](labs/01-embedded-zero-config.md).

### Run without installing .NET

On locked-down hosts or minimal CI images where you do not want a system .NET, bring a
**self-contained** RavenDB build (it bundles its own runtime). Point the server at the extracted
`Server` folder: the driver detects the bundled runtime and launches the server's native apphost
directly, never calling `dotnet`.

```python
from ravendb_embedded import EmbeddedServer, ServerOptions

options = ServerOptions()
options.with_external_server("/path/to/extracted/Server")   # a self-contained build

with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store("MyDb") as store:
        ...
```

Download the Server package for your platform from the [RavenDB downloads page](https://ravendb.net/downloads);
the server files live in the archive's `Server/` folder. Runnable walkthrough:
[`labs/02-embedded-external-server.md`](labs/02-embedded-external-server.md).

Or skip the manual download and let the driver fetch and cache one for you on first use:

```python
options = ServerOptions()
options.with_on_demand_server()   # downloads + caches a self-contained server, no .NET needed
```

Walkthrough: [`labs/03-on-demand-server.md`](labs/03-on-demand-server.md).

### Don't manage a server at all (tests)

For test suites that should not touch .NET or embedded startup, `ravendb-test-driver` can attach
to a RavenDB you run yourself (Docker, testcontainers, a shared CI service) while still giving
each test its own database. See the
[`ravendb-python-testdriver`](https://github.com/ravendb/ravendb-python-testdriver) repository.

## Configuration

### `ServerOptions`

Create `ServerOptions()` and set attributes:

- `data_directory`: where database data is stored (defaults to a local `RavenDB` folder). Set a
  stable path for data that outlives the process, see
  [`labs/05-embedded-persistent.md`](labs/05-embedded-persistent.md).
- `server_url`: the URL to bind (defaults to localhost on a free port).
- `dot_net_path`: path to `dotnet` when it is not on `PATH` (ignored on the self-contained path).
- `command_line_args`: extra [server command-line arguments](https://ravendb.net/docs/article-page/latest/csharp/server/configuration/command-line-arguments).
- `framework_version`: pin an exact .NET version (advanced; leave empty to autodetect the installed runtime).

### Security

Secure the server with `ServerOptions.secured()`:

```python
options = ServerOptions()
options.secured(
    server_pfx_certificate_path,      # server certificate (.pfx), required
    client_pem_certificate_path,      # client certificate (.pem)
    server_pfx_certificate_password=None,
    ca_certificate_path=None,
)
```

Runnable example (HTTPS + client-certificate auth):
[`labs/04-embedded-secured.md`](labs/04-embedded-secured.md).

### Working with data

`get_document_store(database_name)` returns a `DocumentStore` you use like any RavenDB client. For
finer control, build a `DatabaseOptions` (via `DatabaseOptions.from_database_name`) and call
`get_document_store_from_options`; set `skip_creating_database=True` to not auto-create the
database.

Call `open_studio_in_browser()` to open RavenDB Studio in your default browser.

## Labs

The `labs/` folder holds runnable, self-checking guides, one per usage case above. Start at
[`labs/README.md`](labs/README.md).
