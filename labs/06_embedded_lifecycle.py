"""Lab 06: Stop, restart, process IDs, and process-exit notifications."""

import tempfile
from pathlib import Path
from threading import Event

from ravendb_embedded import EmbeddedServer, ServerOptions


def main() -> None:
    with tempfile.TemporaryDirectory() as work:
        options = ServerOptions()
        options.data_directory = str(Path(work, "data"))
        options.logs_path = str(Path(work, "logs"))

        exit_observed = Event()
        exit_events = []

        def on_server_exit(event) -> None:
            exit_events.append(event)
            exit_observed.set()

        with EmbeddedServer() as server:
            server.add_server_process_exited(on_server_exit)
            server.start_server(options)
            first_process_id = server.get_server_process_id()
            print(f"Started RavenDB process {first_process_id}")

            server.stop_server()
            if not exit_observed.wait(10):
                raise RuntimeError("The server exit callback was not invoked.")

            stopped = exit_events[-1]
            assert stopped.process_id == first_process_id
            assert stopped.expected
            print(f"Stopped RavenDB process {stopped.process_id}")

            exit_observed.clear()
            server.restart_server()
            second_process_id = server.get_server_process_id()
            assert second_process_id != first_process_id
            print(f"Restarted RavenDB as process {second_process_id}")

            with server.get_document_store("LifecycleLab") as store:
                with store.open_session() as session:
                    session.store({"status": "running"}, "status/1")
                    session.save_changes()

        print("PASS: stop, exit notification, restart, and document access succeeded.")


if __name__ == "__main__":
    main()
