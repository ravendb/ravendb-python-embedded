import json
import os
import pkgutil
import shutil
import zipfile
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Union


class ProvideRavenDBServer(ABC):
    @abstractmethod
    def provide(self, target_directory: str) -> None:
        pass


class CopyServerProvider(ProvideRavenDBServer):
    def __init__(self, server_files: str):
        self.server_files = server_files

    def provide(self, target_directory: str) -> None:
        if os.path.abspath(self.server_files) == os.path.abspath(target_directory):
            return  # already in place: run the server where it is, nothing to copy
        try:
            shutil.copytree(self.server_files, target_directory)
        except FileExistsError:
            pass


class CopyServerFromNugetProvider(CopyServerProvider):
    SERVER_FILES = Path("target/nuget/contentFiles/any/any/RavenDBServer")

    def __init__(self):
        module_path = Path(__file__).parent
        super().__init__(os.path.join(module_path, self.SERVER_FILES))

    def provide(self, target_directory: str) -> None:
        if not os.path.exists(target_directory):
            raise RuntimeError(
                f"Unable to find 'target' directory in the current working directory ({os.path.abspath('.')}). "
                f"Please make sure you execute the test in the ravendb_embedded directory with the provide.py file."
            )

        super().provide(target_directory)


class ExtractFromZipServerProvider(ProvideRavenDBServer):
    def __init__(self, source_location: str):
        self.source_location = source_location

    def provide(self, target_directory):
        os.makedirs(target_directory, exist_ok=True)
        with open(self.source_location, "rb") as zip_file:
            self.unzip(zip_file, target_directory)

    @staticmethod
    def unzip(source: Union[str, bytes], out: str) -> None:
        if isinstance(source, bytes):
            source = BytesIO(source)

        destination = Path(out).resolve()

        def is_inside_destination(name: str) -> bool:
            resolved = (destination / name).resolve()
            return resolved == destination or destination in resolved.parents

        with zipfile.ZipFile(source, "r") as zipped:
            for name in zipped.namelist():
                if not is_inside_destination(name):
                    raise RuntimeError(f"Refusing to extract unsafe archive path: {name}")
            zipped.extractall(out)


class ExtractFromPkgResourceServerProvider(ProvideRavenDBServer):
    def provide(self, target_directory):
        resource_name = "ravendb_server.zip"

        resource_data = pkgutil.get_data(self.__class__.__module__, resource_name)

        if resource_data is None:
            raise RuntimeError(f"Unable to find resource: {resource_name}")

        with BytesIO(resource_data) as bytes_buffer:
            ExtractFromZipServerProvider.unzip(bytes_buffer.read(), target_directory)


class ExternalServerProvider(ProvideRavenDBServer):
    SERVER_DLL_FILENAME = "Raven.Server.dll"
    SERVER_SFA_FILENAME = "Raven.Server"

    def __init__(self, server_location: str):
        self.server_location = server_location
        self.is_single_file_app = False

        file_server_location = os.path.abspath(server_location)

        if not os.path.exists(file_server_location):
            raise ValueError(f"Server location doesn't exist: {server_location}")

        if os.path.isfile(file_server_location):
            self.inner_provider = ExtractFromZipServerProvider(server_location)
            return

        # Check self-contained first: it also ships Raven.Server.dll, so a .dll-first check
        # would misroute it to `dotnet` and force a system .NET install.
        if os.path.isdir(file_server_location):
            if self._is_self_contained(file_server_location):
                self.is_single_file_app = True
                self.inner_provider = CopyServerProvider(server_location)
                return

            if os.path.exists(os.path.join(file_server_location, self.SERVER_DLL_FILENAME)):
                self.inner_provider = CopyServerProvider(server_location)
                return

        raise ValueError(
            f"Unable to find RavenDB server (expected directory with {self.SERVER_DLL_FILENAME}) or zip file. "
            f"Used directory = {server_location}"
        )

    @staticmethod
    def _is_self_contained(directory: str) -> bool:
        # Self-contained marker: `includedFrameworks` in the runtime config, or an apphost
        # present with no managed .dll.
        runtime_config = os.path.join(directory, "Raven.Server.runtimeconfig.json")
        if os.path.isfile(runtime_config):
            try:
                with open(runtime_config, encoding="utf-8") as config_file:
                    runtime_options = json.load(config_file).get("runtimeOptions", {})
                if runtime_options.get("includedFrameworks"):
                    return True
            except (OSError, ValueError):
                pass

        has_managed_dll = os.path.exists(os.path.join(directory, ExternalServerProvider.SERVER_DLL_FILENAME))
        has_apphost = any(
            os.path.exists(os.path.join(directory, name))
            for name in (
                ExternalServerProvider.SERVER_SFA_FILENAME,
                f"{ExternalServerProvider.SERVER_SFA_FILENAME}.exe",
            )
        )
        return has_apphost and not has_managed_dll

    def provide(self, target_directory: str) -> None:
        self.inner_provider.provide(target_directory)
