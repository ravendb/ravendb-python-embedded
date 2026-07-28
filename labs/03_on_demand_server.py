"""Lab 03: On-demand, cached self-contained server (no manual download, no .NET).

For: Lab 02 (no system .NET) without downloading and extracting a server yourself. Call
`with_auto_downloaded_server()`; on first use the driver fetches a self-contained build for this
platform, caches it, and reuses the cache next time. Because the build is self-contained it runs
its native apphost and never calls `dotnet`.

Run:  python labs/03_on_demand_server.py
"""

import tempfile
from pathlib import Path

from ravendb_embedded import EmbeddedServer, ServerOptions


def main() -> None:
    with tempfile.TemporaryDirectory() as work:
        options = ServerOptions()
        options.dot_net_path = "__no_dotnet__"
        options.with_auto_downloaded_server()
        options.data_directory = str(Path(work, "data"))
        options.logs_path = str(Path(work, "logs"))

        with EmbeddedServer() as server:
            server.start_server(options)
            with server.get_document_store("Lab") as store:
                with store.open_session() as session:
                    session.store({"name": "Ayende"}, "people/1")
                    session.save_changes()
                with store.open_session() as session:
                    assert session.load("people/1", dict)["name"] == "Ayende"

    print("Lab 03 OK: on-demand self-contained server, cached and run with no system .NET.")


if __name__ == "__main__":
    main()
