from pyravendb.custom_exceptions.exceptions import InvalidOperationException
from raven_embedded.server_options import ServerOptions
from pyravendb.tools.utils import Utils
import subprocess
import signal
import os


class RavenServerRunner:
    @staticmethod
    def run(server_options: ServerOptions):
        if not server_options.server_directory:
            raise ValueError("server_options.server_directory cannot be None or empty")
        if not server_options.data_directory:
            raise ValueError("server_options.data_directory cannot be None or empty")

        server_dll_path = os.path.join(server_options.server_directory, "Raven.Server.dll")
        if not os.path.isfile(server_dll_path):
            raise FileNotFoundError("Server file was not found", server_dll_path)

        if not server_options.dotnet_path:
            raise ValueError("server_options.dotnet_path cannot be None or empty")

        server_options.command_line_args.append("--Embedded.ParentProcessId=" + str(os.getpid()))
        server_options.command_line_args.append("--License.Eula.Accepted=" + str(server_options.accept_eula))
        server_options.command_line_args.append("--Setup.Mode=None")
        server_options.command_line_args.append("--DataDir=" + server_options.data_directory)

        if server_options.security:
            if not server_options.server_url:
                server_options.server_url = "https://127.0.0.1:0"
            server_options.command_line_args.append("--ServerUrl=" + server_options.server_url)
            if server_options.security.certificate_path is not None:
                server_options.command_line_args.append(
                    "--Security.Certificate.Path=" + server_options.security.certificate_path)
            else:
                server_options.command_line_args.append(
                    "--Security.Certificate.Exec=" + server_options.security.certificate_exec)
                server_options.command_line_args.append(
                    "--Security.Certificate.Exec.Arguments=" + server_options.security.certificate_arguments)
            server_options.command_line_args.append(
                "--Security.WellKnownCertificates.Admin=" + Utils.get_cert_file_fingerprint(
                    server_options.security.client_certificate))
        else:
            if not server_options.server_url:
                server_options.server_url = "http://127.0.0.1:0"
            server_options.command_line_args.append("--ServerUrl=" + server_options.server_url)

        server_options.command_line_args[0:0] = [server_dll_path]
        server_options.command_line_args[0:0] = ["--fx-version " + server_options.framework_version]

        server_options.command_line_args[0:0] = [server_options.dotnet_path]
        argument_string = " ".join(server_options.command_line_args)
        try:
            process = subprocess.Popen(argument_string,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
        except Exception as e:
            process.send_signal(signal.SIGINT)
            raise InvalidOperationException(
                "Unable to execute server." + os.linesep + "Command was:" + os.linesep + argument_string, e)

        return process
