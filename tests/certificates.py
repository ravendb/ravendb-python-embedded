import datetime
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def generate_self_signed_certificates(directory):
    """Write server.pfx, client.pem and ca.crt into `directory`; return their paths.

    The certificate carries the extensions RavenDB requires of a server certificate:
    DigitalSignature key usage, serverAuth/clientAuth EKU, and SANs for how the embedded
    server is reached (localhost + 127.0.0.1). The same cert doubles as the client cert,
    which the server then trusts as a well-known admin certificate.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
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
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()
    )

    server_pfx = Path(directory, "server.pfx")
    client_pem = Path(directory, "client.pem")
    ca_crt = Path(directory, "ca.crt")
    server_pfx.write_bytes(
        pkcs12.serialize_key_and_certificates(b"localhost", key, certificate, None, serialization.NoEncryption())
    )
    client_pem.write_bytes(key_pem + certificate_pem)
    ca_crt.write_bytes(certificate_pem)
    return str(server_pfx), str(client_pem), str(ca_crt)
