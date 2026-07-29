import os
import re
import subprocess

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID
from ravendb.exceptions.raven_exceptions import RavenException

from ravendb_embedded.options import ServerOptions
from ravendb_embedded.runtime_framework_version_matcher import (
    RuntimeFrameworkVersionMatcher,
)


class RavenServerRunner:
    _CERTIFICATE_PATTERN = re.compile(
        rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
        re.DOTALL,
    )
    _PRIVATE_KEY_PATTERN = re.compile(
        rb"-----BEGIN (?:RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY-----.*?"
        rb"-----END (?:RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY-----",
        re.DOTALL,
    )

    @staticmethod
    def run(options: ServerOptions) -> subprocess.Popen:
        client_certificate = RavenServerRunner._validate_security_options(options)

        if not options.target_server_location.strip():
            raise ValueError("target_server_location cannot be None or whitespace")

        if not options.data_directory.strip():
            raise ValueError("data_directory cannot be None or whitespace")

        if not options.logs_path.strip():
            raise ValueError("logs_path cannot be None or whitespace")

        is_sfa = getattr(options.provider, "is_single_file_app", False)
        if is_sfa:
            # Self-contained / single-file build: run the native apphost, no `dotnet`.
            file_name = "Raven.Server.exe" if os.name == "nt" else "Raven.Server"
        else:
            file_name = "Raven.Server.dll"

        server_paths = [
            f"{file_name}",
            f"Server/{file_name}",
            f"contentFiles/any/any/RavenDBServer/{file_name}",
        ]

        server_file_path = None

        for path in server_paths:
            full_path = os.path.join(options.target_server_location, path)
            if os.path.exists(full_path):
                server_file_path = full_path
                break

        if server_file_path is None:
            raise RavenException("Server file was not found in any of the expected locations.")

        if not options.dot_net_path.strip():
            raise ValueError("dot_net_path cannot be None or whitespace")

        # Args are passed to Popen as a list (no shell), so they need no manual escaping.
        command_line_args = [
            f"--Embedded.ParentProcessId={RavenServerRunner.get_process_id()}",
            f"--License.Eula.Accepted={'true' if options.accept_eula else 'false'}",
            f"--License.DisableAutoUpdate={'true' if options.licensing.disable_auto_update else 'false'}",
            (
                "--License.DisableAutoUpdateFromApi="
                f"{'true' if options.licensing.disable_auto_update_from_api else 'false'}"
            ),
            (
                "--License.DisableLicenseSupportCheck="
                f"{'true' if options.licensing.disable_license_support_check else 'false'}"
            ),
            (
                "--License.ThrowOnInvalidOrMissingLicense="
                f"{'true' if options.licensing.throw_on_invalid_or_missing_license else 'false'}"
            ),
            "--Setup.Mode=None",
            f"--DataDir={options.data_directory}",
            f"--Logs.Path={options.logs_path}",
        ]

        if options.licensing.license is not None:
            command_line_args.append(f"--License={options.licensing.license}")
        if options.licensing.license_path is not None:
            command_line_args.append(f"--License.Path={options.licensing.license_path}")

        if options.security:
            options.server_url = options.server_url or "https://127.0.0.1:0"

            if options.security.server_pfx_certificate_path:
                command_line_args.append(f"--Security.Certificate.Path={options.security.server_pfx_certificate_path}")

                if options.security.server_pfx_certificate_password:
                    command_line_args.append(
                        f"--Security.Certificate.Password={options.security.server_pfx_certificate_password}"
                    )
            elif options.security.certificate_exec:
                command_line_args.extend(
                    [
                        f"--Security.Certificate.Load.Exec={options.security.certificate_exec}",
                        f"--Security.Certificate.Load.Exec.Arguments={options.security.certificate_arguments}",
                    ]
                )
            if client_certificate:
                thumbprint = client_certificate.fingerprint(hashes.SHA1()).hex().upper()
                command_line_args.append(f"--Security.WellKnownCertificates.Admin={thumbprint}")
        else:
            options.server_url = options.server_url or "http://127.0.0.1:0"

        command_line_args.extend([f"--ServerUrl={options.server_url}"])

        command_line_args[:0] = options.command_line_args
        command_line_args.insert(0, server_file_path)
        if not is_sfa:
            command_line_args.insert(0, options.dot_net_path)

            requested_framework = options.framework_version
            if requested_framework == RuntimeFrameworkVersionMatcher.AUTO:
                requested_framework = RuntimeFrameworkVersionMatcher.required_framework_version(server_file_path)

            if requested_framework:
                framework_version = RuntimeFrameworkVersionMatcher.match(options, requested_framework)
                command_line_args.insert(1, framework_version)
                command_line_args.insert(1, "--fx-version")

        try:
            process_builder = subprocess.Popen(
                command_line_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as error:
            if is_sfa:
                raise
            raise RuntimeError(
                f"Unable to execute the .NET host '{options.dot_net_path}'. Install the required .NET runtime, "
                "set ServerOptions.dot_net_path, or use with_auto_downloaded_server() to run without system .NET."
            ) from error
        process = process_builder

        return process

    @staticmethod
    def _validate_security_options(options: ServerOptions) -> x509.Certificate | None:
        security = options.security
        if security is None:
            return None
        if not security.client_pem_certificate_path:
            raise ValueError(
                "A secured embedded server requires client_pem_certificate_path. "
                "The server PFX is not automatically reused as a client certificate."
            )

        client_path = security.client_pem_certificate_path
        try:
            with open(client_path, "rb") as client_file:
                client_data = client_file.read()
        except OSError as error:
            raise ValueError(f"Unable to read the client PEM certificate '{client_path}': {error}") from error

        certificate_match = RavenServerRunner._CERTIFICATE_PATTERN.search(client_data)
        if certificate_match is None:
            raise ValueError(f"Client PEM '{client_path}' does not contain an X.509 certificate.")
        try:
            certificate = x509.load_pem_x509_certificate(certificate_match.group(), default_backend())
        except ValueError as error:
            raise ValueError(f"Client PEM '{client_path}' contains an invalid X.509 certificate.") from error

        key_match = RavenServerRunner._PRIVATE_KEY_PATTERN.search(client_data)
        if key_match is None:
            raise ValueError(f"Client PEM '{client_path}' does not contain a private key.")
        try:
            private_key = serialization.load_pem_private_key(key_match.group(), password=None)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Client PEM '{client_path}' must contain a valid, unencrypted private key.") from error

        public_format = serialization.PublicFormat.SubjectPublicKeyInfo
        certificate_key = certificate.public_key().public_bytes(serialization.Encoding.DER, public_format)
        private_key_public = private_key.public_key().public_bytes(serialization.Encoding.DER, public_format)
        if certificate_key != private_key_public:
            raise ValueError(f"The certificate and private key in client PEM '{client_path}' do not match.")

        try:
            extended_key_usage = certificate.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value
        except x509.ExtensionNotFound:
            pass
        else:
            if ExtendedKeyUsageOID.CLIENT_AUTH not in extended_key_usage:
                raise ValueError(f"Client certificate '{client_path}' does not allow TLS client authentication.")

        if security.ca_certificate_path:
            ca_path = security.ca_certificate_path
            try:
                with open(ca_path, "rb") as ca_file:
                    ca_data = ca_file.read()
            except OSError as error:
                raise ValueError(f"Unable to read the CA certificate bundle '{ca_path}': {error}") from error

            ca_certificates = RavenServerRunner._CERTIFICATE_PATTERN.findall(ca_data)
            if not ca_certificates:
                raise ValueError(f"CA certificate bundle '{ca_path}' does not contain an X.509 certificate.")
            try:
                for ca_certificate in ca_certificates:
                    x509.load_pem_x509_certificate(ca_certificate, default_backend())
            except ValueError as error:
                raise ValueError(f"CA certificate bundle '{ca_path}' contains an invalid certificate.") from error

        return certificate

    @staticmethod
    def get_process_id() -> str:
        return str(os.getpid())
