# Lab 04: Secured embedded server (HTTPS + client certificate)

**For:** running the embedded server with TLS and client-certificate authentication instead of
plain HTTP. You bring a server certificate (`.pfx`) and a client certificate (`.pem`);
`ServerOptions.secured()` wires them in, and the driver hands you a store already configured with
the client cert, so your session code does not change.

## Run it

```bash
pip install ravendb-embedded
python labs/04_embedded_secured.py
```

The complete example is [`04_embedded_secured.py`](04_embedded_secured.py). The core is:

```python
from ravendb_embedded import EmbeddedServer, ServerOptions
from ravendb_embedded.options import DatabaseOptions

options = ServerOptions()
options.accept_eula = True
options.secured(server_pfx_path, client_pem_path, ca_certificate_path=ca_crt_path)

with EmbeddedServer() as server:
    server.start_server(options)
    with server.get_document_store_from_options(DatabaseOptions.from_database_name("Lab")) as store:
        # store.urls[0] is now https://...; the client certificate is already attached
        ...
```

## Certificates

`secured()` needs a server `.pfx` and a client `.pem`; a password and a CA certificate are
optional. In production you bring your own (for example from RavenDB's setup wizard or your CA).
The lab generates a throwaway self-signed pair so it can run unattended; that generator is demo
code, not something to ship. A RavenDB server certificate needs the right extensions
(digitalSignature key usage, serverAuth/clientAuth EKU, and SANs for how the server is reached),
which the lab's generator sets.

## Takeaway

Securing the embedded server is one `secured()` call plus certificates. Everything after
`get_document_store` is ordinary RavenDB client code, now over HTTPS with client-certificate auth.
