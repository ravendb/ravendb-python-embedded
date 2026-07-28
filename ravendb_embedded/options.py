from __future__ import annotations

import os
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


class ServerOptions:
    BASE_MODULE_DIRECTORY = str(Path(__file__).parent)
    DEFAULT_SERVER_LOCATION = os.path.join(BASE_MODULE_DIRECTORY, CopyServerFromNugetProvider.SERVER_FILES)

    def __init__(self):
        self.framework_version: Optional[str] = ""
        self.logs_path: str = self.BASE_MODULE_DIRECTORY + "/RavenDB/Logs"
        self.data_directory: str = self.BASE_MODULE_DIRECTORY + "/RavenDB"
        self.provider: ProvideRavenDBServer = CopyServerFromNugetProvider()
        self.target_server_location: str = self.DEFAULT_SERVER_LOCATION
        self.dot_net_path: str = "dotnet"
        self.clear_target_server_location: bool = False
        self.accept_eula: bool = True
        self.server_url: Optional[str] = None
        self.graceful_shutdown_timeout: timedelta = timedelta(seconds=30)
        self.process_kill_timeout: timedelta = timedelta(seconds=5)
        self.max_server_startup_time_duration: timedelta = timedelta(minutes=1)
        self.command_line_args: list[str] = list()
        self.security: Optional[SecurityOptions] = None

    @classmethod
    def INSTANCE(cls):
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
