import contextlib

import starboard

import peachtree
import peachtree.server
from . import provider_tests
from .qemu_tests import provider_with_user_networking as qemu_provider

import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


@contextlib.contextmanager
def _create_remote_provider():
    with qemu_provider() as underlying_provider:
        port = starboard.find_local_free_tcp_port()
        with peachtree.server.start_server(port=port, provider=underlying_provider):
            with peachtree.remote_provider(hostname="localhost", port=port) as provider:
                yield provider


RemoteTests = provider_tests.create("RemoteTests", _create_remote_provider)
