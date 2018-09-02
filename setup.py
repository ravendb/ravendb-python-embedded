from setuptools import setup, find_packages

setup(
    name='pyravendb-embedded',
    packages=find_packages(),
    long_description=open('README.rst').read(),
    version='4.1.1.4',
    description='RavenDB Embedded library to run ravendb in embedded way',
    author='RavenDB',
    author_email='support@ravendb.net',
    url='https://github.com/ravendb/ravendb-python-embedded',
    license='Custom EULA',
    keywords='pyravendb embedded database nosql doc db',
    install_requires=
    [
        'pyravendb >= 4.0.4.9',
    ],
    include_package_data=True,
    zip_safe=False
)
