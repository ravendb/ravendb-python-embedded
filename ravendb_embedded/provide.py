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
        try:
            shutil.copytree(self.server_files, target_directory)
        except FileExistsError:
            pass


class CopyServerFromNugetProvider(CopyServerProvider):
    SERVER_FILES = "target\\nuget\\contentFiles\\any\\any\\RavenDBServer"

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
        # Ensure the target directory exists
        os.makedirs(target_directory, exist_ok=True)
        with open(self.source_location, "rb") as zip_file:
            self.unzip(zip_file, target_directory)

    @staticmethod
    def unzip(source: Union[str, bytes], out: str) -> None:
        with zipfile.ZipFile(source, "r") as zipped:
            zipped.extractall(out)


class ExtractFromPkgResourceServerProvider(ProvideRavenDBServer):
    def provide(self, target_directory):
        resource_name = "ravendb_server.zip"

        # Get binary data from the resource
        resource_data = pkgutil.get_data(self.__class__.__module__, resource_name)

        if resource_data is None:
            raise RuntimeError(f"Unable to find resource: {resource_name}")

        # Create a bytes buffer from the binary data
        with BytesIO(resource_data) as bytes_buffer:
            # Call the unzip method to extract contents to the target directory
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

        # Check if target is a file - assuming it is a zip file
        if os.path.isfile(file_server_location):
            self.inner_provider = ExtractFromZipServerProvider(server_location)
            return

        # Alternatively, it might be a directory - look for Raven.Server.exe inside
        if os.path.isdir(file_server_location) and os.path.exists(
            os.path.join(file_server_location, self.SERVER_DLL_FILENAME)
        ):
            self.inner_provider = CopyServerProvider(server_location)
            return

        # Also look for Single File App file - Raven.Server
        if os.path.isdir(file_server_location) and os.path.exists(
            os.path.join(file_server_location, self.SERVER_SFA_FILENAME)
        ):
            self.is_single_file_app = True
            self.inner_provider = CopyServerProvider(server_location)
            return



        raise ValueError(
            f"Unable to find RavenDB server (expected directory with {self.SERVER_DLL_FILENAME}) or zip file. "
            f"Used directory = {server_location}"
        )

    def provide(self, target_directory: str) -> None:
        self.inner_provider.provide(target_directory)
