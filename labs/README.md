# RavenDB Python: test server labs

Ways to get a RavenDB server for your tests, from most convenient to most portable.
Pick the one that matches your environment.

| Lab | Path | For whom | Needs system .NET? |
|-----|------|----------|--------------------|
| [01](01-embedded-zero-config.md) | Embedded, zero-config | Local dev or CI on a machine that already has .NET | Yes (.NET 10 for 7.2.x) |
| [02](02-embedded-external-server.md) | External self-contained server | You do not want to install .NET at all | No |
| 03 | Attach to a server you run yourself (Docker, testcontainers, shared CI) | Containerized CI pipelines | No |
| [04](04-on-demand-server.md) | On-demand cached self-contained download (exploration) | Lab 02 without the manual download | No |

Lab 03 (attach) lives in the [`ravendb-python-testdriver`](https://github.com/ravendb/ravendb-python-testdriver)
repository, since attaching to an external server is a test-driver feature. Lab 04 is an
exploration and is not wired into the package default.

RavenDB version to .NET mapping: **7.1.x needs .NET 8, 7.2.x needs .NET 10.** The bundled
server is the deciding factor, so this can change on a minor bump; always check the lab for
your version.

Every lab ships a runnable script next to it, so you can run the exact code the guide shows.
