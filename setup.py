from setuptools import setup, find_packages

setup(
    name="pyravendb-embedded",
    packages=find_packages(),
    long_description=open("README.rst").read(),
    version="6.0.0",
    description="RavenDB Embedded library to run ravendb in embedded way",
    author="RavenDB",
    author_email="support@ravendb.net",
    url="https://github.com/ravendb/ravendb-python-embedded",
    license="Custom EULA",
    keywords="ravendb embedded database nosql doc db",
    install_requires=[],
    include_package_data=True,
    zip_safe=False,
)
