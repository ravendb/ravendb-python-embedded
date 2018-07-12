## Overview
PyRaven-Embedded is a RavnenDB package for running RavenDB in embedded mode.

```python
EmbeddedServer().start_server()
with EmbeddedServer().get_document_store("Embedded") as store:
    with store.open_session() as session:
        session.store(User(name="Ilay", age=4))
        session.save_changes()
``` 

## Installation
Install from [PyPi](https://pypi.python.org/pypi), as [pyraven-embedded](https://pypi.python.org/project/pyraven-embedded).
```bash
pip install pyravendb
```
Install PyRaven-Embedded from pip will provide you with a copy of RavenDB server binaries files as well

## Usage
#### Start a server
To start RavenDB server you only need to run start_server()` method from `EmbeddedServer` instance and that's it.
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
* **command_line_args** - A list of all [server command args](https://ravendb.net/docs/article-page/4.0/csharp/server/configuration/command-line-arguments).
```python
server_options = ServerOptions(data_directory="MYPATH/RavenDBDataDir")
EmbeddedServer().start_server(server_options)
```
##### Security
There are two options to make ravendb secured in PyRaven-Embedded:<br />
1) `secured(certificate_path, certificate_password=None)` - For this option you will put a path to a .pfx file for the server and a password to the file
if you have one.
    ```python
    server_options = ServerOptions()
    server_options.secured("PATH_TO_PFX_CERT_FILE", "PASSWORD_TO_CERT_FILE")
    EmbeddedServer.start_server(server_options)
    ```
2) `secured_with_exec(self, cert_exec, cert_exec_args, server_cert_fingerprint, client_cert_path,
                          client_cert_password=None)` - For this option you will have to put executable program (ex. powershell, python, etc) and the arguments for him,
                          the fingerprint of the cert file you can use pyravendb Utils for that (see get_cert_file_fingerprint method), 
                          the client cert path and the password if you have one.
    ```python
    server_options = ServerOptions()
    sserver_options.secured_with_exec("powershell", 
                                     "C:\\secrets\\give_me_cert.ps1",
                                     Utils.get_cert_file_fingerprint("PATH_TO_PEM_CERT_FILE"), 
                                     "PATH_TO_PEM_CERT_FILE")
    EmbeddedServer.start_server(server_options)
    ```

#### Get Document Store
After initialize and start the server we can use `get_document_store` method to be able to get a DocumentStore
and start work with RavenDB as normal.
```python
EmbeddedServer().start_server()
with EmbeddedServer().get_document_store("Test") as store:
    # Your code here
```
`get_document_store` method can get or only the database_name or DatabaseOption
##### DatabaseOptions
* **database_name** - The name of the database
* **skip_creating_database** - `get_document_store` will create a new database if the database is not exists,
if this option if True we won't create the database (Default False).

```python
# In this example we won't create the Test database if not exists will raise an exception

database_options = DatabaseOptions(database_name="Test", skip_creating_database=True)
with EmbeddedServer().get_document_store(database_options) as store:
    # Your code here
```

#### Open the RavenDB studio in the browser
To open RavenDB studio from PyRaven-Embedded you can use `open_studio_in_browser` method and the studio will open automatically
one your default browser.

```python
EmbeddedServer().open_studio_in_browser()
```

## Acknowledgments
**EmbeddedServer** class is a singleton! <br />
Every time we use `EmbeddedServer()` we will get the same instance.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details




