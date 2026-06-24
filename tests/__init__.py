import os


class Person:
    def __init__(self, Id: str = None, name: str = None):
        self.Id = Id
        self.name = name


def pin_framework_version(server_options):
    # CI's .NET-version matrix sets RAVENDB_TEST_FRAMEWORK_VERSION to force the server onto a
    # specific runtime (e.g. "10.0.x"); a no-op locally when it's unset.
    framework_version = os.environ.get("RAVENDB_TEST_FRAMEWORK_VERSION")
    if framework_version:
        server_options.framework_version = framework_version
    return server_options
