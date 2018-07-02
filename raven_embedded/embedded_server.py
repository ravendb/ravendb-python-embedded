from raven_embedded.server_options import ServerOptions
from raven_embedded.ravenserver_runner import RavenServerRunner
import pkg_resources
import logging

logger = logging.getLogger("Embedded")
logger.setLevel(logging.INFO)

# create a file handler
handler = logging.FileHandler('Embedded.log')
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)


class EmbeddedServer:

    def __init__(self):
        self._certificate = None
        self._documentStores = {}

    @staticmethod
    def instance():
        return EmbeddedServer()

    def start_server(self, server_options=None):
        if server_options is None:
            server_options = ServerOptions()

        start_server = self._run_server(server_options)

    def _run_server(self, server_options):
        process = RavenServerRunner.run(server_options)
        return ""
