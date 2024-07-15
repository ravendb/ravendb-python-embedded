import os
import subprocess

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from ravendb.exceptions.raven_exceptions import RavenException

from ravendb_embedded.provide import ExternalServerProvider
from ravendb_embedded.options import ServerOptions
from ravendb_embedded.runtime_framework_version_matcher import (
    RuntimeFrameworkVersionMatcher,
)


class CommandLineArgumentEscaper:
    @staticmethod
    def escape_single_arg(arg: str) -> str:
        return arg  # lol


class RavenServerRunner:
    @staticmethod
    def run(options: ServerOptions) -> subprocess.Popen:
        if not options.target_server_location.strip():
            raise ValueError("target_server_location cannot be None or whitespace")

        if not options.data_directory.strip():
            raise ValueError("data_directory cannot be None or whitespace")

        if not options.logs_path.strip():
            raise ValueError("logs_path cannot be None or whitespace")

        is_sfa = isinstance(options.provider, ExternalServerProvider) and options.provider.is_single_file_app
        file_name = "Raven.Server" if is_sfa else "Raven.Server.dll"

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

        command_line_args = [
            f"--Embedded.ParentProcessId={RavenServerRunner.get_process_id('0')}",
            f"--License.Eula.Accepted={'true' if options.accept_eula else 'false'}",
            "--Setup.Mode=None",
            f"--DataDir={CommandLineArgumentEscaper.escape_single_arg(options.data_directory)}",
            f"--Logs.Path={CommandLineArgumentEscaper.escape_single_arg(options.logs_path)}",
        ]

        if options.security:
            options.server_url = options.server_url or "https://127.0.0.1:0"

            if options.security.server_pfx_certificate_path:
                command_line_args.extend(
                    [
                        f"--Security.Certificate.Path="
                        f"{CommandLineArgumentEscaper.escape_single_arg(options.security.server_pfx_certificate_path)}"
                    ]
                )

                if options.security.server_pfx_certificate_password:
                    command_line_args.extend(
                        [
                            "--Security.Certificate.Password="
                            + CommandLineArgumentEscaper.escape_single_arg(
                                options.security.server_pfx_certificate_password
                            )
                        ]
                    )
            elif options.security.certificate_exec:
                command_line_args.extend(
                    [
                        f"--Security.Certificate.Exec="
                        f"{CommandLineArgumentEscaper.escape_single_arg(options.security.certificate_exec)}",
                        f"--Security.Certificate.Exec.Arguments="
                        f"{CommandLineArgumentEscaper.escape_single_arg(options.security.certificate_arguments)}",
                    ]
                )
            if options.security.client_pem_certificate_path:
                with open(options.security.client_pem_certificate_path, "rb") as cert_file:
                    cert_data = cert_file.read()

                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                thumbprint = cert.fingerprint(hashes.SHA256()).hex()

                command_line_args.extend(
                    [
                        f"--Security.WellKnownCertificates.Admin="
                        f"{CommandLineArgumentEscaper.escape_single_arg(thumbprint)}"
                    ]
                )
        else:
            options.server_url = options.server_url or "http://127.0.0.1:0"

        command_line_args.extend([f"--ServerUrl={options.server_url}"])

        command_line_args[:0] = options.command_line_args
        command_line_args.insert(0, server_file_path)
        if not is_sfa:
            command_line_args.insert(0, options.dot_net_path)

            if options.framework_version:
                framework_version = RuntimeFrameworkVersionMatcher.match(options)
                command_line_args.insert(1, framework_version)
                command_line_args.insert(1, "--fx-version")

        process_builder = subprocess.Popen(command_line_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process = process_builder

        return process

    @staticmethod
    def get_process_id(fallback: str) -> str:
        try:
            return str(os.getpid())
        except Exception:
            return fallback
