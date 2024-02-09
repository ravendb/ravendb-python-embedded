========
Overview
========

``ravendb-embedded`` is a RavenDB package for running RavenDB in embedded mode.

.. code-block:: python

    EmbeddedServer().start_server()
    with EmbeddedServer().get_document_store("Embedded") as store:
        with store.open_session() as session:
            session.store(User(name="Ilay", age=4))
            session.save_changes()

============
Installation
============

Install ``ravendb-embedded`` from `PyPi <https://pypi.python.org/pypi>`_ using:

.. code-block:: bash

    pip install ravendb-embedded

Installing ``ravendb-embedded`` from pip will also provide you with a copy of the RavenDB server binary files.

========
Usage
========

Start a server
--------------

To start the RavenDB server, call the ``start_server()`` method from an ``EmbeddedServer`` instance.

.. code-block:: python

    EmbeddedServer.start_server()

For more control over your server, you can pass ``server_options`` to the ``start_server()`` method.

ServerOptions
-------------

- ``framework_version``: The framework version to run the server with.
- ``data_directory``: Where to save the database data (if None, the files will be saved in the RavenDB folder in the base folder).
- ``server_url``: The URL the server will be opened on (if None, the server will open on localhost).
- ``dotnet_path``: The location of ``dotnet.exe`` (if .NET Core is not installed on your machine, you can download `dotnet binaries <https://www.microsoft.com/net/download/windows>`_ and provide the path).
- ``command_line_args``: A list of all `server command arguments <https://ravendb.net/docs/article-page/6.0/csharp/server/configuration/command-line-arguments>`_.

.. code-block:: python

    server_options = ServerOptions(data_directory="MYPATH/RavenDBDataDir")
    EmbeddedServer().start_server(server_options)

Security
--------

You can secure ``ravendb-embedded`` using the ``secured()`` method:

.. code-block:: python

    secured(server_pfx_certificate_path, client_pem_certificate_path, server_pfx_certificate_password=None, ca_certificate_path=None)

- Provide the path to ``.pfx`` and ``.pem`` files, and optionally a password and CA certificate file.
- Minimal setup requires both a ``.pfx`` server and a ``.pem`` client certificate.

Get Document Store
------------------

After initializing and starting the server, you can use the ``get_document_store`` method to obtain a ``DocumentStore`` and start working with RavenDB as usual.

``get_document_store`` method can take either just the ``database_name`` or ``DatabaseOptions``.

DatabaseOptions
---------------

- ``database_name``: The name of the database.
- ``skip_creating_database``: ``get_document_store`` will create a new database if it does not exist. If this option is set to True, the database won't be created (Default False).

Open RavenDB Studio in the Browser
-----------------------------------

To open RavenDB Studio from ``ravendb-embedded``, use the ``open_studio_in_browser`` method, and the studio will open automatically in your default browser.
