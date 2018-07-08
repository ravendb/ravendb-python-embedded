from setuptools import setup, find_packages

setup(
    name='pyravenembedded',
    packages=find_packages(),
    version='4.1.0.1',
    description='RavenDB Embedded library to run ravendb in embedded way',
    author='Idan Haim Shalom',
    author_email='haimdude@gmail.com',
    url='https://github.com/ravendb/RavenDB-Python-Client',
    license='MIT',
    keywords='pyravendb embedded database nosql doc db',
    install_requires=
    [
        'pyravendb >= 4.0.4.2',
    ],
    include_package_data=True,
    zip_safe=False
)
