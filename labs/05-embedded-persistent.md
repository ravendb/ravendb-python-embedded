# Lab 05: Persistent data directory (data survives restarts)

**For:** using the embedded server as a durable local database rather than a throwaway. Point
`data_directory` at a fixed folder and your databases and documents live there, still present the
next time you start the server against the same folder.

## Run it

```bash
pip install ravendb-embedded
python labs/05_embedded_persistent.py
```

The complete example is [`05_embedded_persistent.py`](05_embedded_persistent.py). The core is:

```python
from ravendb_embedded import EmbeddedServer, ServerOptions

def options(data_directory, logs_path):
    o = ServerOptions()
    o.data_directory = data_directory   # a fixed folder you reuse across restarts
    o.logs_path = logs_path
    return o

# First run: write, then shut down.
with EmbeddedServer() as server:
    server.start_server(options(data_directory, logs_path))
    with server.get_document_store("Lab") as store:
        ...  # store a document

# Later run against the SAME data_directory: the document is still there.
with EmbeddedServer() as server:
    server.start_server(options(data_directory, logs_path))
    with server.get_document_store("Lab") as store:
        ...  # load it back
```

## Notes

- The default `data_directory` remains `RavenDB` inside the installed package directory. Set it
  explicitly when the package directory may be read-only or the application needs a fixed,
  application-owned location.
- `get_document_store("Lab")` reuses the existing database on the second run; it only creates one
  when it is missing.

## Takeaway

Embedded is not in-memory. Give it a stable `data_directory` and it behaves like a normal local
RavenDB whose data outlives the process.
