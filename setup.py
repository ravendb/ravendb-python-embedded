from setuptools import setup, find_packages

with open("README.md") as file:
    long_description = file.read()

setup(
    name='pyravendb-embedded',
    packages=find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    version='4.1.0.2',
    description='RavenDB Embedded library to run ravendb in embedded way',
    author='HibernatingRhinos',
    author_email='support@ravendb.net',
    url='https://github.com/ravendb/RavenDB-Python-Client',
    license='MIT',
    keywords='pyravendb embedded database nosql doc db',
    install_requires=
    [
        'pyravendb >= 4.0.4.5',
    ],
    include_package_data=True,
    zip_safe=False
)
