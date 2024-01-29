
## Overview
ravendb-embedded is a RavenDB  package for running RavenDB in embedded mode.

```python
from ravendb_embedded .embedded_server import EmbeddedServer

EmbeddedServer().start_server()
with EmbeddedServer().get_document_store("Embedded") as store:
    with store.open_session() as session:
        session.store(User(name="Ilay", age=4))
        session.save_changes()
``` 

## Installation
Install from [PyPi](https://pypi.python.org/pypi), as [ravendb-embedded](https://pypi.python.org/project/ravendb-embedded).
```bash
pip install ravendb_embedded
```
Install ravendb-embedded from pip will provide you with a copy of RavenDB server binaries files as well.

## Usage
#### Start a server
To start RavenDB server you only need to run `start_server()` method from `EmbeddedServer` instance and that's it.
```python
EmbeddedServer.start_server()
```
To be more in control about your server `start_server` method can take one parameter `server_options`.
##### ServerOptions
* **framework_version** - The framework version to run the server with.
* **data_directory** - Where to save the database data (if None the files will be saved in RavenDB folder in the base folder).
* **server_url** - The url the server will be opened if None the server will open on local host.
* **dotnet_path** - Where dotnet.exe is located if dotnet in the PATH nothing needed here (If .net core is not installed in your machine
you can download [dotnet binaries](https://www.microsoft.com/net/download/windows) and just put the path to it)
* **command_line_args** - A list of all [server command args](https://ravendb.net/docs/article-page/6.0/csharp/server/configuration/command-line-arguments).
```python
from ravendb_embedded .options import ServerOptions
from ravendb_embedded .embedded_server import EmbeddedServer

server_options = ServerOptions(data_directory="MYPATH/RavenDBDataDir")
EmbeddedServer().start_server(server_options)
```
##### Security
There are options to make ravendb secured in ravendb-embedded:<br />
1) `secured(server_pfx_certificate_path, client_pem_certificate_path, server_pfx_certificate_password=None, ca_certificate_path)` - For this option you will put path to a .pfx and .pem files and a password/ca cert
if you have one.
    ```python
    from ravendb_embedded .options import ServerOptions
    from ravendb_embedded .embedded_server import EmbeddedServer
   
    server_options = ServerOptions()
    server_options.secured("PATH_TO_PFX_CERT_FILE", "PASSWORD_TO_CERT_FILE")
    EmbeddedServer.start_server(server_options)
    ```

[//]: # (2&#41; `secured_with_exec&#40;self, cert_exec, cert_exec_args, server_cert_fingerprint, client_cert_path,)

[//]: # (                          client_cert_password=None&#41;` - For this option you will have to put executable program &#40;ex. powershell, python, etc&#41; and the arguments for him,)

[//]: # (                          the fingerprint of the cert file you can use pyravendb Utils for that &#40;see get_cert_file_fingerprint method&#41;, )

[//]: # (                          the client cert path and the password if you have one.)

[//]: # (    ```python)

[//]: # (    server_options = ServerOptions&#40;&#41;)

[//]: # (    sserver_options.secured_with_exec&#40;"powershell", )

[//]: # (                                     "C:\\secrets\\give_me_cert.ps1",)

[//]: # (                                     Utils.get_cert_file_fingerprint&#40;"PATH_TO_PEM_CERT_FILE"&#41;, )

[//]: # (                                     "PATH_TO_PEM_CERT_FILE"&#41;)

[//]: # (    EmbeddedServer.start_server&#40;server_options&#41;)

[//]: # (    ```)

#### Get Document Store
After initialize and start the server we can use `get_document_store` method to be able to get a DocumentStore
and start work with RavenDB as normal.

```python
from ravendb_embedded .embedded_server import EmbeddedServer

EmbeddedServer().start_server()
with EmbeddedServer().get_document_store("Test") as store:
# Your code here
```
`get_document_store` method can get a database_name or DatabaseOption
##### DatabaseOptions
* **database_name** - The name of the database
* **skip_creating_database** - `get_document_store` will create a new database if the database is not exists,
if this option if True we won't create the database (Default False).

```python
# In this example we won't create the Test database if not exists will raise an exception
from ravendb_embedded .options import DatabaseOptions
from ravendb_embedded .embedded_server import EmbeddedServer

database_options = DatabaseOptions.from_database_name("Test")
database_options.skip_creating_database=True
with EmbeddedServer().get_document_store_from_options(database_options) as store:
# Your code here
```

#### Open RavenDB studio in the browser
To open RavenDB studio from ravendb-embedded you can use `open_studio_in_browser` method and the studio will open automatically
one your default browser.

```python
from ravendb_embedded .embedded_server import EmbeddedServer

EmbeddedServer().open_studio_in_browser()
```

## Acknowledgments
**EmbeddedServer** class is a singleton! <br />
Every time we use `EmbeddedServer()` we will get the same instance.




