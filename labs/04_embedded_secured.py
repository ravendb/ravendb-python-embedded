"""Lab 04: Secured embedded server (HTTPS + client-certificate auth).

For: running the embedded server with TLS and client-certificate authentication instead of plain
HTTP. Point `ServerOptions.secured()` at a server certificate (.pfx) and a client certificate
(.pem); the driver wires the client cert into the store, so your session code is unchanged.

In production you bring your own certificates. This lab generates a throwaway self-signed pair so
it can run unattended.

Run:  python labs/04_embedded_secured.py
"""

import datetime
import ipaddress
import shutil
import tempfile
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from ravendb_embedded import EmbeddedServer, ServerOptions
from ravendb_embedded.options import DatabaseOptions


def _demo_certificates(directory):
    """Throwaway self-signed server.pfx + client.pem (demo only; bring your own in production).

    Carries what RavenDB requires of a server certificate: digitalSignature key usage,
    serverAuth/clientAuth EKU, and SANs for how the embedded server is reached (localhost,
    127.0.0.1). The same cert doubles as the trusted admin client certificate.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()
    )
    server_pfx, client_pem, ca_crt = (
        Path(directory, "server.pfx"),
        Path(directory, "client.pem"),
        Path(directory, "ca.crt"),
    )
    server_pfx.write_bytes(
        pkcs12.serialize_key_and_certificates(b"localhost", key, cert, None, serialization.NoEncryption())
    )
    client_pem.write_bytes(key_pem + cert_pem)
    ca_crt.write_bytes(cert_pem)
    return str(server_pfx), str(client_pem), str(ca_crt)


def main() -> None:
    work = tempfile.mkdtemp()
    try:
        server_pfx, client_pem, ca_crt = _demo_certificates(work)

        options = ServerOptions()
        options.secured(server_pfx, client_pem, ca_certificate_path=ca_crt)  # HTTPS + client-cert auth
        options.data_directory = str(Path(work, "RavenDB"))
        options.logs_path = str(Path(work, "Logs"))

        with EmbeddedServer() as server:
            server.start_server(options)
            with server.get_document_store_from_options(DatabaseOptions.from_database_name("Lab")) as store:
                assert store.urls[0].startswith("https://"), store.urls
                with store.open_session() as session:
                    session.store({"name": "Ayende"}, "people/1")
                    session.save_changes()
                with store.open_session() as session:
                    assert session.load("people/1", dict)["name"] == "Ayende"
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("Lab 04 OK: secured embedded server over HTTPS with client-certificate auth.")


if __name__ == "__main__":
    main()
