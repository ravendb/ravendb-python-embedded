========
Overview
========
Ravendb-Embedded is a RavenDB  package for running RavenDB in embedded mode.

.. code-block:: python

    EmbeddedServer().start_server()
    with EmbeddedServer().get_document_store("Embedded") as store:
        with store.open_session() as session:
            session.store(User(name="Ilay", age=4))
            session.save_changes()

============
Installation
============
Install from `PyPi <https://pypi.python.org/pypi>`_, as `ravendb-embedded_ <https://pypi.python.org/project/ravendb-embedded>`_.

.. code-block:: bash

    pip install pyravendb

Install Ravendb-Embedded from pip will provide you with a copy of RavenDB server binaries files as well.

========
Usage
========
Start a server
--------------
To start RavenDB server you only need to run ``start_server()`` method from ``EmbeddedServer`` instance and that's it.

.. code-block:: python

   EmbeddedServer.start_server()

To be more in control about your server `start_server` method can take one parameter `server_options`.

ServerOptions
-------------
* **framework_version** - The framework version to run the server with.
* **data_directory** - Where to save the database data (if None the files will be saved in RavenDB folder in the base folder).
* **server_url** - The url the server will be opened if None the server will open on local host.
* **dotnet_path** - Where dotnet.exe is located if dotnet in the PATH nothing needed here (If .net core is not installed in your machine
                    you can download `dotnet binaries <https://www.microsoft.com/net/download/windows>`_ and just put the path to it)
* **command_line_args** - A list of all `server command args <https://ravendb.net/docs/article-page/6.0/csharp/server/configuration/command-line-arguments>`_.

.. code-block:: python

    server_options = ServerOptions(data_directory="MYPATH/RavenDBDataDir")
    EmbeddedServer().start_server(server_options)

Security
--------
There are two options to make ravendb secured in Ravendb-Embedded:

1. `secured(server_pfx_certificate_path, client_pem_certificate_path, server_pfx_certificate_password=None, ca_certificate_path)` - For this option you will put path to a .pfx and .pem files and a password/ca cert
if you have one.

Get Document Store
----------------------
After initialize and start the server we can use ``get_document_store`` method to be able to get a DocumentStore
and start work with RavenDB as normal.

.. code-block:: python

        EmbeddedServer().start_server()
        with EmbeddedServer().get_document_store("Test") as store:
            pass

``get_document_store`` method can get or only the database_name or DatabaseOption

DatabaseOptions
---------------
* **database_name** - The name of the database
* **skip_creating_database** - ``get_document_store`` will create a new database if the database is not exists, if this option if True we won't create the database (Default False).

.. code-block:: python

    # In this example we won't create the Test database if not exists will raise an exception

    database_options = DatabaseOptions(database_name="Test", skip_creating_database=True)
    with EmbeddedServer().get_document_store(database_options) as store:
      # Your code here

Open the RavenDB studio in the browser
--------------------------------------------
To open RavenDB studio from Pyravendb-Embedded you can use ``open_studio_in_browser`` method and the studio will open automatically
one your default browser.

.. code-block:: python

   EmbeddedServer().open_studio_in_browser()

================
Acknowledgments
================
**EmbeddedServer** class is a singleton!

Every time we use ``EmbeddedServer()`` we will get the same instance.




