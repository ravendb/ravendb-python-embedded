"""Lab 05: Persistent data directory (data survives restarts).

For: using the embedded server as a durable local database, not a throwaway. Point
`data_directory` at a fixed folder; the databases and documents live there and are still present
the next time you start the server against the same folder.

Run:  python labs/05_embedded_persistent.py
"""

import shutil
import tempfile
from pathlib import Path

from ravendb_embedded import EmbeddedServer, ServerOptions


def _options(data_directory, logs_path):
    options = ServerOptions()
    options.accept_eula = True
    options.data_directory = data_directory
    options.logs_path = logs_path
    return options


def main() -> None:
    root = tempfile.mkdtemp()
    data_directory = str(Path(root, "RavenDB"))
    logs_path = str(Path(root, "Logs"))
    try:
        # First run: write a document, then shut the server down (context exit stops it).
        with EmbeddedServer() as server:
            server.start_server(_options(data_directory, logs_path))
            with server.get_document_store("Lab") as store:
                with store.open_session() as session:
                    session.store({"name": "Ayende"}, "people/1")
                    session.save_changes()

        # Second run against the SAME data_directory: the document is still there.
        with EmbeddedServer() as server:
            server.start_server(_options(data_directory, logs_path))
            with server.get_document_store("Lab") as store:
                with store.open_session() as session:
                    loaded = session.load("people/1", dict)
                    assert loaded is not None and loaded["name"] == "Ayende", loaded
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("Lab 05 OK: the document written in the first run survived a full server restart.")


if __name__ == "__main__":
    main()
