
## Overview
ravendb-embedded is a RavenDB  package for running RavenDB in embedded mode.

```python
from ravendb_embedded import EmbeddedServer

EmbeddedServer().start_server()
with EmbeddedServer().get_document_store("Embedded") as store:
    with store.open_session() as session:
        session.store(User(name="Ilay", age=4))
        session.save_changes()
``` 

## Installation
Install from [PyPi](https://pypi.python.org/pypi), as [ravendb-embedded](https://pypi.python.org/project/ravendb-embedded).
```bash
pip install ravendb-embedded
```
Install ravendb-embedded from pip will provide you with a copy of RavenDB server binaries files as well.

## Usage
#### Start a server
To start RavenDB server, call `start_server()` method from `EmbeddedServer` instance.
```python
from ravendb_embedded import EmbeddedServer

ravendb_server = EmbeddedServer()
ravendb_server.start_server()
```
To be more in control about your server `start_server` method can take `server_options`.


#### ServerOptions
* **framework_version** - The framework version to run the server with.
* **data_directory** - Where to save the database data (if None the files will be saved in RavenDB folder in the base folder).
* **server_url** - The url the server will be opened if None the server will open on local host.
* **dotnet_path** - Where dotnet.exe is located if dotnet in the PATH nothing needed here (If .net core is not installed in your machine
you can download [dotnet binaries](https://www.microsoft.com/net/download/windows) and just put the path to it)
* **command_line_args** - A list of all [server command args](https://ravendb.net/docs/article-page/6.0/csharp/server/configuration/command-line-arguments).
```python
from ravendb_embedded import EmbeddedServer, ServerOptions

server_options = ServerOptions(data_directory="MYPATH/RavenDBDataDir")
EmbeddedServer().start_server(server_options)
```
---
##### Security
There are options to make ravendb secured in ravendb-embedded:<br />

`secured(server_pfx_certificate_path, client_pem_certificate_path, server_pfx_certificate_password=None, ca_certificate_path = None)` 
- For this option you will put path to a .pfx and .pem files and a password/ca cert if you have one.
- Server certificate password and CA cert file are optional arguments. Minimal setup requires both .pfx server and .pem client certificates.
    ```python
    from ravendb_embedded import EmbeddedServer, ServerOptions
   
    server_options = ServerOptions()
    server_options.secured("PATH_TO_SERVER_PFX_CERT_FILE", "PATH_TO_CLIENT_PEM_CERT")
    EmbeddedServer.start_server(server_options)
    ```
---
#### Get Document Store
After initialize and start the server we can use `get_document_store` method to be able to get a DocumentStore
and start work with RavenDB as normal.

```python
from ravendb_embedded import EmbeddedServer

ravendb_server = EmbeddedServer()
ravendb_server.start_server()

with ravendb_server.get_document_store("Test") as store:
# Your code here
```
---

##### DatabaseOptions
* **database_name** - The name of the database
* **skip_creating_database** - `get_document_store` will create a new database if the database is not exists,
if this option if True we won't create the database (Default False).

```python
# In this example we won't create the Test database if not exists will raise an exception
from ravendb_embedded import EmbeddedServer, DatabaseOptions

ravendb_server = EmbeddedServer()
ravendb_server.start_server()

database_options = DatabaseOptions.from_database_name("Test")
database_options.skip_creating_database = True

with ravendb_server.get_document_store_from_options(database_options) as store:
# Your code here
```

#### Open RavenDB studio in the browser
To open RavenDB studio from ravendb-embedded you can use `open_studio_in_browser` method and the studio will open automatically
one your default browser.

```python
from ravendb_embedded import EmbeddedServer
ravendb_server = EmbeddedServer()
ravendb_server.start_server()

ravendb_server.open_studio_in_browser()
```
