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


provider = peachtree.qemu_provider()

@istest
def can_run_commands_on_vm():
    port = starboard.find_local_free_tcp_port()
    with peachtree.server.start_server(port=port, provider=provider):
        with peachtree.remote_provider(hostname="localhost", port=port) as client:
            with client.start(_IMAGE_NAME) as machine:
                shell = machine.shell()
                result = shell.run(["echo", "Hello there"])
                assert_equals("Hello there\n", result.output)


@istest
def machine_is_not_running_after_context_manager_for_machine_exits():
    port = starboard.find_local_free_tcp_port()
    with peachtree.server.start_server(port=port, provider=provider):
        with peachtree.remote_provider(hostname="localhost", port=port) as client:
            with client.start(_IMAGE_NAME) as machine:
                assert machine.is_running()
            assert not machine.is_running()
