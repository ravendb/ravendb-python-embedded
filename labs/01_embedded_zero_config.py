"""Lab 01: Embedded, zero-config.

For: local development or CI on a machine that already has .NET installed.
You want `pip install ravendb-embedded` and a working RavenDB server, no extra setup.

Requirement: RavenDB 7.2.x needs .NET 10 (7.1.x needed .NET 8).
Check your runtime with:  dotnet --list-runtimes   (look for Microsoft.NETCore.App 10.0.x)

Run:  python labs/01_embedded_zero_config.py
"""

import tempfile
from pathlib import Path

from ravendb_embedded import EmbeddedServer, ServerOptions


def main() -> None:
    with tempfile.TemporaryDirectory() as work_dir:
        options = ServerOptions()
        options.accept_eula = True
        options.data_directory = str(Path(work_dir, "RavenDB"))
        options.logs_path = str(Path(work_dir, "Logs"))

        with EmbeddedServer() as server:
            server.start_server(options)
            with server.get_document_store("Lab") as store:
                with store.open_session() as session:
                    session.store({"name": "Ayende"}, "people/1")
                    session.save_changes()

                with store.open_session() as session:
                    loaded = session.load("people/1", dict)
                    assert loaded["name"] == "Ayende", loaded

    print("Lab 01 OK: embedded server started, wrote and read a document.")


if __name__ == "__main__":
    main()
