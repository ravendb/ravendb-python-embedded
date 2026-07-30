# Lab 06: Server lifecycle and process monitoring

**For:** applications that need to stop or restart their managed RavenDB process and observe
whether a process exit was expected or unexpected.

## Run it

```bash
pip install ravendb-embedded
python labs/06_embedded_lifecycle.py
```

The complete, self-checking example is
[`06_embedded_lifecycle.py`](06_embedded_lifecycle.py). It exercises:

- `get_server_process_id()`
- `stop_server()`
- `restart_server()`
- `add_server_process_exited()`
- document access after restart

The core lifecycle flow is:

```python
from threading import Event

from ravendb_embedded import EmbeddedServer, ServerOptions

options = ServerOptions()

exit_observed = Event()
exit_events = []

with EmbeddedServer() as server:
    server.add_server_process_exited(
        lambda event: (exit_events.append(event), exit_observed.set())
    )
    server.start_server(options)
    first_process_id = server.get_server_process_id()

    server.stop_server()
    assert exit_observed.wait(10)
    assert exit_events[-1].process_id == first_process_id
    assert exit_events[-1].expected

    server.restart_server()
    assert server.get_server_process_id() != first_process_id
```

`event.expected` is `True` for `stop_server()`, `restart_server()`, and context-manager cleanup.
It is `False` when RavenDB exits on its own.

## Takeaway

`EmbeddedServer` owns the RavenDB child process but exposes enough lifecycle information for an
application to coordinate restarts and distinguish planned shutdowns from server failures.
