"""Lab 02: External self-contained server (no system .NET).

For: machines or CI that do NOT have .NET installed. You bring a self-contained RavenDB
server build (it bundles the .NET runtime), and the driver runs its native apphost directly,
never calling `dotnet`.

Get the Server package for your platform from the RavenDB downloads page
(https://ravendb.net/downloads), extract it; the server files live in the `Server/` subfolder.

Run:
  RAVENDB_SELF_CONTAINED_SERVER=/path/to/extracted/Server python labs/02_embedded_external_server.py
"""

import os
import sys
import tempfile
from pathlib import Path

from ravendb_embedded import EmbeddedServer, ServerOptions

SERVER = os.environ.get("RAVENDB_SELF_CONTAINED_SERVER") or (sys.argv[1] if len(sys.argv) > 1 else None)
if not SERVER:
    sys.exit("Set RAVENDB_SELF_CONTAINED_SERVER (or pass a path) to the extracted 'Server' folder. See the header.")


def main() -> None:
    with tempfile.TemporaryDirectory() as work:
        options = ServerOptions()
        options.accept_eula = True
        options.data_directory = str(Path(work, "data"))
        options.logs_path = str(Path(work, "logs"))
        # Bogus on purpose: a self-contained build must never call `dotnet`, so if it still boots the no-.NET path works.
        options.dot_net_path = "__no_dotnet__"
        options.with_external_server(SERVER)

        with EmbeddedServer() as server:
            server.start_server(options)
            with server.get_document_store("Lab") as store:
                with store.open_session() as session:
                    session.store({"name": "Ayende"}, "people/1")
                    session.save_changes()

                with store.open_session() as session:
                    assert session.load("people/1", dict)["name"] == "Ayende"

    print("Lab 02 OK: self-contained server ran with NO system .NET.")


if __name__ == "__main__":
    main()
