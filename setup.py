from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
import os
import urllib.request
from tqdm import tqdm

# Modify the RavenDB version and download URL accordingly
RAVENDB_VERSION = "6.0.0"
RAVENDB_DOWNLOAD_URL = f"https://www.nuget.org/api/v2/package/RavenDB.Embedded/{RAVENDB_VERSION}"
RAVENDB_DOWNLOAD_FOLDER = "downloaded_ravendb"
RAVENDB_FULL_DOWNLOAD_PATH = os.path.join(RAVENDB_DOWNLOAD_FOLDER, "ravendb-server")


# Function to download RavenDB with progress bar
def download_ravendb_with_progress():
    os.makedirs(RAVENDB_DOWNLOAD_FOLDER, exist_ok=True)

    response = urllib.request.urlopen(RAVENDB_DOWNLOAD_URL)
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024  # Adjust the block size as needed
    progress_bar = tqdm(total=total_size, unit="B", unit_scale=True)

    with open(RAVENDB_FULL_DOWNLOAD_PATH, "wb") as file, progress_bar:
        while True:
            buffer = response.read(block_size)
            if not buffer:
                break

            file.write(buffer)
            progress_bar.update(len(buffer))


# Custom installation command to download RavenDB before installation
class CustomInstall(install):
    def run(self):
        download_ravendb_with_progress()
        super().run()


# Custom develop command to download RavenDB before development
class CustomDevelop(develop):
    def run(self):
        download_ravendb_with_progress()
        super().run()


# Setup configuration
setup(
    name="ravendb-embedded",
    packages=find_packages(),
    long_description=open("README.rst").read(),
    version=RAVENDB_VERSION,
    description="RavenDB Embedded library to run RavenDB in an embedded way",
    author="RavenDB",
    author_email="support@ravendb.net",
    url="https://github.com/ravendb/ravendb-python-embedded",
    license="Custom EULA",
    keywords="ravendb embedded database nosql doc db",
    install_requires=[],
    include_package_data=True,
    zip_safe=False,
    package_data={"": ["ravendb-server/*"]},
    cmdclass={"install": CustomInstall, "develop": CustomDevelop},
)
