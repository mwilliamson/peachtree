import contextlib

import starboard

import peachtree
import peachtree.server
from . import provider_tests

import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


underlying_provider = peachtree.qemu_provider()

@contextlib.contextmanager
def _create_remote_provider():
    port = starboard.find_local_free_tcp_port()
    with peachtree.server.start_server(port=port, provider=underlying_provider):
        with peachtree.remote_provider(hostname="localhost", port=port) as provider:
            yield provider


RemoteProviderTests = provider_tests.create("RemoteTests", _create_remote_provider)
