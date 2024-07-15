from setuptools import setup
import zipfile

import os
import urllib.request
from setuptools.command.sdist import sdist

RAVENDB_VERSION = "5.4.200"
ZIP_FILE_NAME = "server.zip"
RAVENDB_DOWNLOAD_URL = f"https://www.nuget.org/api/v2/package/RavenDB.Embedded/{RAVENDB_VERSION}"

RAVENDB_DOWNLOAD_FOLDER = "ravendb_embedded/target/nuget"
RAVENDB_FULL_DOWNLOAD_PATH = os.path.join(RAVENDB_DOWNLOAD_FOLDER, ZIP_FILE_NAME)


def download_and_unpack_ravendb():
    os.makedirs(RAVENDB_DOWNLOAD_FOLDER, exist_ok=True)

    response = urllib.request.urlopen(RAVENDB_DOWNLOAD_URL)
    file_content = response.read()

    with open(RAVENDB_FULL_DOWNLOAD_PATH, "wb") as file:
        file.write(file_content)

    # Unzip the downloaded file
    with zipfile.ZipFile(RAVENDB_FULL_DOWNLOAD_PATH, "r") as zip_ref:
        zip_ref.extractall(RAVENDB_DOWNLOAD_FOLDER)

    # Remove the server.zip file
    os.remove(RAVENDB_FULL_DOWNLOAD_PATH)


# Custom source distribution command to ensure server.zip is included
class CustomSDist(sdist):
    def run(self):
        download_and_unpack_ravendb()
        super().run()


setup(
    python_requires=">=3.7",
    cmdclass={"sdist": CustomSDist},
    name="ravendb-embedded",
    packages=["ravendb_embedded"],
    package_dir={"ravendb_embedded": "ravendb_embedded"},
    include_package_data=True,
    long_description=open("README.rst").read(),
    version="5.2.6.post1",
    description="RavenDB Embedded library to run RavenDB in an embedded way",
    author="RavenDB",
    author_email="support@ravendb.net",
    url="https://github.com/ravendb/ravendb-python-embedded",
    license="Custom EULA",
    keywords="ravendb embedded database nosql doc db",
    install_requires=[
        "ravendb==5.2.6",
        "cryptography~=42.0.0",
    ],
    zip_safe=False,
)
