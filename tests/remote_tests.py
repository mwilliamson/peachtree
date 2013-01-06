import os
import contextlib
import time

from nose.tools import istest, assert_equals
from hamcrest import assert_that, contains, has_property, is_not
import spur
import starboard

import peachtree
import peachtree.server

from .tempdir import create_temporary_dir

import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


_IMAGE_NAME="ubuntu-precise-amd64"


underlying_provider = peachtree.qemu_provider()

@istest
def can_run_commands_on_vm():
    with _create_remote_provider() as provider:
        with provider.start(_IMAGE_NAME) as machine:
            shell = machine.shell()
            result = shell.run(["echo", "Hello there"])
            assert_equals("Hello there\n", result.output)


@istest
def machine_is_not_running_after_context_manager_for_machine_exits():
    with _create_remote_provider() as provider:
        with provider.start(_IMAGE_NAME) as machine:
            assert machine.is_running()
        assert not machine.is_running()


@contextlib.contextmanager
def _create_remote_provider():
    port = starboard.find_local_free_tcp_port()
    with peachtree.server.start_server(port=port, provider=underlying_provider):
        with peachtree.remote_provider(hostname="localhost", port=port) as provider:
            yield provider
