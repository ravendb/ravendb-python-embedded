# ravendb-embedded: labs

Runnable, self-checking guides for getting a RavenDB server, from most convenient to most
portable. Each lab ships a script next to it, so you can run the exact code the guide shows.

The scripts are part of this repository and are not installed into `site-packages`. Clone or
download the repository first, then run the commands below from its root; `pip install` supplies
the released library and server binaries used by the scripts.

| Lab | Covers | Needs system .NET? |
|-----|--------|--------------------|
| [01](01-embedded-zero-config.md) | Embedded, zero-config (the default) | Yes (.NET 10 for 7.2.x) |
| [02](02-embedded-external-server.md) | External self-contained server you provide | No |
| [03](03-on-demand-server.md) | On-demand cached self-contained download (no manual steps) | No |
| [04](04-embedded-secured.md) | Secured embedded server (HTTPS + client certificate) | Yes |
| [05](05-embedded-persistent.md) | Persistent data directory (data survives restarts) | Yes |
| [06](06-embedded-lifecycle.md) | Stop, restart, PID, and process-exit monitoring | Yes |

RavenDB version to .NET mapping: **7.1.x needs .NET 8, 7.2.x needs .NET 10.** The bundled server
decides this, so it can change on a minor bump; check the lab for your version.

Want the driver to attach to a server you run yourself (Docker, testcontainers, shared CI) instead
of running one? That is a test-driver feature and has its own lab in the
[`ravendb-python-testdriver`](https://github.com/ravendb/ravendb-python-testdriver) package.
