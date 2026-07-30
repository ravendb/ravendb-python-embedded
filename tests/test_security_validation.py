import datetime
import tempfile
from pathlib import Path
from unittest import TestCase

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID, NameOID

from ravendb_embedded import ServerOptions
from ravendb_embedded.raven_server_runner import RavenServerRunner
from tests.certificates import generate_separate_server_and_client_certificates


class TestSecurityValidation(TestCase):
    def test_generated_certificate_chain_has_matching_key_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            server_pfx, client_pem, _ = generate_separate_server_and_client_certificates(directory)
            _, server_certificate, ca_certificates = pkcs12.load_key_and_certificates(
                Path(server_pfx).read_bytes(), None
            )
            ca_certificate = ca_certificates[0]
            client_pem_bytes = Path(client_pem).read_bytes()
            client_certificate = x509.load_pem_x509_certificate(
                client_pem_bytes[client_pem_bytes.index(b"-----BEGIN CERTIFICATE-----") :]
            )

            ca_key_identifier = ca_certificate.extensions.get_extension_for_oid(
                ExtensionOID.SUBJECT_KEY_IDENTIFIER
            ).value.digest
            for certificate in (server_certificate, client_certificate):
                authority_key_identifier = certificate.extensions.get_extension_for_oid(
                    ExtensionOID.AUTHORITY_KEY_IDENTIFIER
                ).value.key_identifier
                self.assertEqual(authority_key_identifier, ca_key_identifier)

    def test_secured_allows_server_only_configuration(self):
        options = ServerOptions().secured("server.pfx")

        self.assertEqual(options.security.server_pfx_certificate_path, "server.pfx")
        self.assertIsNone(options.security.client_pem_certificate_path)

    def test_client_pem_must_contain_a_private_key(self):
        with tempfile.TemporaryDirectory() as directory:
            _, certificate = self._create_certificate([ExtendedKeyUsageOID.CLIENT_AUTH])
            client_pem = Path(directory, "client.pem")
            client_pem.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))

            options = self._secured_options(client_pem)
            with self.assertRaisesRegex(ValueError, "does not contain a private key"):
                RavenServerRunner.run(options)

    def test_client_certificate_and_private_key_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            first_key, _ = self._create_certificate([ExtendedKeyUsageOID.CLIENT_AUTH])
            _, second_certificate = self._create_certificate([ExtendedKeyUsageOID.CLIENT_AUTH])
            client_pem = Path(directory, "client.pem")
            client_pem.write_bytes(
                self._private_key_pem(first_key) + second_certificate.public_bytes(serialization.Encoding.PEM)
            )

            options = self._secured_options(client_pem)
            with self.assertRaisesRegex(ValueError, "do not match"):
                RavenServerRunner.run(options)

    def test_declared_eku_must_allow_client_authentication(self):
        with tempfile.TemporaryDirectory() as directory:
            key, certificate = self._create_certificate([ExtendedKeyUsageOID.SERVER_AUTH])
            client_pem = Path(directory, "client.pem")
            client_pem.write_bytes(self._private_key_pem(key) + certificate.public_bytes(serialization.Encoding.PEM))

            options = self._secured_options(client_pem)
            with self.assertRaisesRegex(ValueError, "does not allow TLS client authentication"):
                RavenServerRunner.run(options)

    def test_ca_path_must_contain_a_certificate(self):
        with tempfile.TemporaryDirectory() as directory:
            key, certificate = self._create_certificate([ExtendedKeyUsageOID.CLIENT_AUTH])
            client_pem = Path(directory, "client.pem")
            client_pem.write_bytes(self._private_key_pem(key) + certificate.public_bytes(serialization.Encoding.PEM))
            ca_path = Path(directory, "ca.crt")
            ca_path.write_text("not a certificate", encoding="utf-8")

            options = self._secured_options(client_pem, ca_path)
            with self.assertRaisesRegex(ValueError, "does not contain an X.509 certificate"):
                RavenServerRunner.run(options)

    def test_ca_is_validated_without_a_managed_client_certificate(self):
        with tempfile.TemporaryDirectory() as directory:
            ca_path = Path(directory, "ca.crt")
            ca_path.write_text("not a certificate", encoding="utf-8")
            options = ServerOptions().secured("server.pfx", ca_certificate_path=str(ca_path))

            with self.assertRaisesRegex(ValueError, "does not contain an X.509 certificate"):
                RavenServerRunner.run(options)

    @staticmethod
    def _secured_options(client_pem: Path, ca_path: Path = None) -> ServerOptions:
        options = ServerOptions()
        options.accept_eula = True
        options.secured(
            "server.pfx",
            str(client_pem),
            ca_certificate_path=str(ca_path) if ca_path else None,
        )
        return options

    @staticmethod
    def _private_key_pem(key) -> bytes:
        return key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )

    @staticmethod
    def _create_certificate(extended_key_usage):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "embedded-client")])
        now = datetime.datetime.now(datetime.timezone.utc)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.ExtendedKeyUsage(extended_key_usage), critical=False)
            .sign(key, hashes.SHA256())
        )
        return key, certificate
