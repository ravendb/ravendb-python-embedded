from __future__ import annotations

import os
import warnings
from datetime import timedelta
from pathlib import Path
from typing import Optional

from ravendb.documents.conventions import DocumentConventions
from ravendb.exceptions.raven_exceptions import RavenException
from ravendb.serverwide.database_record import DatabaseRecord

from ravendb_embedded.provide import (
    ProvideRavenDBServer,
    ExternalServerProvider,
    CopyServerFromNugetProvider,
)
from ravendb_embedded.on_demand import ensure_server


class DatabaseOptions:
    def __init__(self, database_record: DatabaseRecord):
        self.database_record = database_record
        self.skip_creating_database: Optional[bool] = False
        self.conventions: DocumentConventions = DocumentConventions()

    @classmethod
    def from_database_name(cls, database_name: str) -> DatabaseOptions:
        return cls(DatabaseRecord(database_name))


class SecurityOptions:
    def __init__(self):
        self.server_pfx_certificate_path: Optional[str] = None
        self.server_pfx_certificate_password: Optional[str] = None
        self.client_pem_certificate_path: Optional[str] = None
        self.ca_certificate_path: Optional[str] = None
        self.certificate_exec: Optional[str] = None
        self.certificate_arguments: Optional[str] = None


class LicensingOptions:
    def __init__(self):
        self.license: Optional[str] = None
        self.license_path: Optional[str] = None
        self.disable_auto_update: bool = False
        self.disable_auto_update_from_api: bool = False
        self.disable_license_support_check: bool = True
        self.throw_on_invalid_or_missing_license: bool = False


class ServerOptions:
    BASE_MODULE_DIRECTORY = str(Path(__file__).parent)
    DEFAULT_SERVER_LOCATION = os.path.join(BASE_MODULE_DIRECTORY, CopyServerFromNugetProvider.SERVER_FILES)

    def __init__(self):
        self.framework_version: Optional[str] = "auto"
        self._data_directory: str = str(Path.cwd() / "RavenDB")
        self._logs_path: Optional[str] = None
        self.provider: ProvideRavenDBServer = CopyServerFromNugetProvider()
        self.target_server_location: str = self.DEFAULT_SERVER_LOCATION
        self.dot_net_path: str = "dotnet"
        self.clear_target_server_location: bool = False
        self.accept_eula: bool = False
        self.server_url: Optional[str] = None
        self.graceful_shutdown_timeout: timedelta = timedelta(seconds=30)
        self.process_kill_timeout: timedelta = timedelta(seconds=5)
        self.max_server_startup_time_duration: timedelta = timedelta(minutes=1)
        self.command_line_args: list[str] = list()
        self.licensing: LicensingOptions = LicensingOptions()
        self.security: Optional[SecurityOptions] = None

    @property
    def data_directory(self) -> str:
        return self._data_directory

    @data_directory.setter
    def data_directory(self, value: str) -> None:
        self._data_directory = value

    @property
    def logs_path(self) -> str:
        return self._logs_path or str(Path(self._data_directory) / "Logs")

    @logs_path.setter
    def logs_path(self, value: Optional[str]) -> None:
        self._logs_path = value

    @classmethod
    def INSTANCE(cls):
        warnings.warn(
            "ServerOptions.INSTANCE() is deprecated; construct ServerOptions() directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls()

    @classmethod
    def from_external_server(cls, server_location: str) -> ServerOptions:
        instance = cls()
        instance.provider = ExternalServerProvider(server_location)
        return instance

    def secured(
        self,
        server_pfx_certificate_path: str,
        client_pem_certificate_path: str = None,
        server_pfx_certificate_password: str = "",
        ca_certificate_path: str = None,
    ) -> "ServerOptions":
        if server_pfx_certificate_path is None:
            raise ValueError("certificate cannot be None")
        if not client_pem_certificate_path:
            raise ValueError(
                "client_pem_certificate_path is required. A server PFX is not reused automatically "
                "because it may not contain a client-authentication certificate and private key."
            )

        if self.security is not None:
            raise RuntimeError("The security has already been set up for this ServerOptions object")

        try:
            self.security = SecurityOptions()
            self.security.server_pfx_certificate_path = server_pfx_certificate_path
            self.security.server_pfx_certificate_password = server_pfx_certificate_password
            self.security.client_pem_certificate_path = client_pem_certificate_path
            if ca_certificate_path:
                self.security.ca_certificate_path = ca_certificate_path

        except Exception as e:
            raise RavenException(f"Unable to create secured server: {e}", e)

        return self

    def secured_with_certificate_exec(
        self,
        certificate_exec: str,
        certificate_arguments: str,
        client_pem_certificate_path: str,
        ca_certificate_path: str = None,
    ) -> "ServerOptions":
        if certificate_exec is None:
            raise ValueError("certificate_exec cannot be None")
        if certificate_arguments is None:
            raise ValueError("certificate_arguments cannot be None")
        if client_pem_certificate_path is None:
            raise ValueError("client_pem_certificate_path cannot be None")
        if self.security is not None:
            raise RuntimeError("The security has already been set up for this ServerOptions object")

        self.security = SecurityOptions()
        self.security.certificate_exec = certificate_exec
        self.security.certificate_arguments = certificate_arguments
        self.security.client_pem_certificate_path = client_pem_certificate_path
        self.security.ca_certificate_path = ca_certificate_path
        return self

    def with_external_server(self, server_location: str) -> None:
        self.provider = ExternalServerProvider(server_location)
        # A directory is already a runnable server: run it in place, so we neither copy it nor
        # collide with the bundled server sitting at the default target location.
        if os.path.isdir(server_location):
            self.target_server_location = server_location
            self.clear_target_server_location = False  # never wipe the user's own server directory

    def with_auto_downloaded_server(self, version: str = None, cache_root: str = None) -> None:
        # Download (once) and cache a self-contained server, then run it with no system .NET.
        self.with_external_server(ensure_server(version, cache_root))
