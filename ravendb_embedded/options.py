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

    # todo: secured by cert exec and args

    def with_external_server(self, server_location: str) -> None:
        self.provider = ExternalServerProvider(server_location)
