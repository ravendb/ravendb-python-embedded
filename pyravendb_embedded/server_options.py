from pyravendb.custom_exceptions.exceptions import InvalidOperationException
from pyravendb.tools.utils import Utils
from datetime import timedelta
import os


class ServerOptions:
    def __init__(self, framework_version="2.1.2", data_directory=None, server_directory=None, server_url=None,
                 dotnet_path="dotnet", accept_eula=True, max_server_startup_time_duration=timedelta(minutes=1),
                 command_line_args=None, gracefully_exit_timeout = 3):

        self.framework_version = framework_version
        self.data_directory = data_directory if data_directory is not None else os.path.realpath("RavenDB")
        if not server_directory:
            import pyravendb_embedded
            server_directory = os.path.join(os.path.dirname(pyravendb_embedded.__file__), "RavenDBServer")
        self.server_directory = server_directory
        self.server_url = server_url
        self.dotnet_path = dotnet_path
        self.accept_eula = accept_eula
        self.gracefully_exit_timeout = gracefully_exit_timeout
        self.max_server_startup_time_duration = max_server_startup_time_duration
        if command_line_args is None:
            command_line_args = []
        self.command_line_args = command_line_args
        self.security = None

    def secured(self, certificate_path, certificate_password=None):
        """
        :param certificate_path: The path to a pfx file
        :param certificate_password: The password of the certificate file

        :type certificate_path: str
        :type certificate_password: str
        """

        if certificate_path is None:
            raise ValueError("certificate_path cannot be None")

        if self.security is not None:
            raise InvalidOperationException("The security has already been setup for this ServerOptions object")

        server_cert_fingerprint = Utils.get_cert_file_fingerprint(certificate_path)

        client_cert_path = _SecurityOptions.get_pem_file(certificate_path, certificate_password)
        self.security = _SecurityOptions(certificate_path, certificate_password, client_cert_path,
                                         server_cert_fingerprint=server_cert_fingerprint)

    def secured_with_exec(self, cert_exec, cert_exec_args, server_cert_fingerprint, client_cert_path,
                          client_cert_password=None):
        """
        :param cert_exec: The application you need to run the script (ex. powershell, python)
        :param cert_exec_args: The arguments to the exec (ex. the script you want to run)
        :param server_cert_fingerprint: The fingerprint of the file
        :param client_cert_path: The path to the certificate file (can be .pem or .pfx)
        :param client_cert_password: The password of the certificate file if have one
        """

        if cert_exec is None:
            raise ValueError("cert_exec cannot be None")
        if cert_exec_args is None:
            raise ValueError("cert_exec_args cannot be None")
        if server_cert_fingerprint is None:
            raise ValueError("server_cert_fingerprint cannot be None")
        if client_cert_path is None:
            raise ValueError("client_cert_path cannot be None")

        client_cert_path = _SecurityOptions.get_pem_file(client_cert_path, client_cert_password)

        if self.security is not None:
            raise InvalidOperationException("The security has already been setup for this ServerOptions object")

        self.security = _SecurityOptions(client_certificate=client_cert_path, certificate_exec=cert_exec,
                                         certificate_arguments=cert_exec_args,
                                         server_cert_fingerprint=server_cert_fingerprint)


class _SecurityOptions:
    def __init__(self, certificate_path=None, certificate_password=None, client_certificate=None, certificate_exec=None,
                 certificate_arguments=None, server_cert_fingerprint=None):
        self.certificate_path = certificate_path
        self.certificate_password = certificate_password
        self.client_certificate = client_certificate
        self.certificate_exec = certificate_exec
        self.certificate_arguments = certificate_arguments
        self.server_cert_fingerprint = server_cert_fingerprint

    @staticmethod
    def get_pem_file(cert_path, cert_password):
        dir_name, filename = os.path.split(cert_path)
        if filename.lower().endswith(".pfx"):
            return Utils.pfx_to_pem(os.path.join(dir_name, filename.replace(".pfx", ".pem")), cert_path, cert_password)
        return cert_path
