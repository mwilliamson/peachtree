import os
import contextlib

from nose.tools import istest, assert_equal

import peachtree
import peachtree.qemu

from .tempdir import create_temporary_dir
from . import provider_tests

import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


_IMAGE_NAME="ubuntu-precise-amd64"
_WINDOWS_IMAGE_NAME="windows-server-2012-x86-64"


@contextlib.contextmanager
def provider_with_temp_data_dir(networking):
    with create_temporary_dir() as data_dir:
        def _pick_image(name):
            image_path = peachtree.qemu.Images().image_path(name)
            temp_image_path = peachtree.qemu.Images(data_dir).image_path(name)
            if not os.path.exists(os.path.dirname(temp_image_path)):
                os.makedirs(os.path.dirname(temp_image_path))
            os.symlink(image_path, temp_image_path)    
        
        _pick_image(_IMAGE_NAME)
        _pick_image(_WINDOWS_IMAGE_NAME)
        
        provider = peachtree.qemu_provider(networking=networking, data_dir=data_dir)
        try:
            yield provider
        finally:
            for machine in provider.list_running_machines():
                machine.destroy()


def provider_with_user_networking():
    return provider_with_temp_data_dir(peachtree.qemu.UserNetworking())
    

QemuProviderTests = provider_tests.create(
    "QemuProviderTests",
    provider_with_user_networking
)


@istest
def can_start_multiple_machines():
    requests = [
        peachtree.request_machine("first", image_name=_IMAGE_NAME),
        peachtree.request_machine("second", image_name=_IMAGE_NAME),
    ]
    with provider_with_user_networking() as provider:
        with provider.start_many(requests) as machines:
            _assert_can_run_commands_on_machine(machines[0])
            _assert_can_run_commands_on_machine(machines[1])


@istest
def machines_started_at_the_same_time_can_access_each_other_directly_by_name():
    requests = [
        peachtree.request_machine("first", image_name=_IMAGE_NAME),
        peachtree.request_machine("second", image_name=_IMAGE_NAME),
    ]
    with provider_with_user_networking() as provider:
        with provider.start_many(requests) as machines:
            first_machine, second_machine = machines[0], machines[1]
            first_machine.shell().run(["ping", "second", "-c1"])


@istest
def windows_machines_can_join_virtual_network():
    requests = [
        peachtree.request_machine("linux", image_name=_IMAGE_NAME),
        peachtree.request_machine("windows", image_name=_WINDOWS_IMAGE_NAME),
    ]
    with provider_with_user_networking() as provider:
        with provider.start_many(requests) as machines:
            # TODO: change to machines["windows"]
            windows_machine = machines[1]
            windows_machine.shell().run(["ping", "linux", "-n", "1"])


@istest
def running_cron_kills_any_running_machines_past_timeout():
    with provider_with_user_networking() as provider:
        with provider.start(_IMAGE_NAME, timeout=0) as machine:
            provider.cron()
            assert not machine.is_running()


@istest
def cron_does_not_kill_machines_without_timeout():
    with provider_with_user_networking() as provider:
        with provider.start(_IMAGE_NAME) as machine:
            provider.cron()
            assert machine.is_running()


def _assert_can_run_commands_on_machine(machine):
    shell = machine.shell()
    result = shell.run(["echo", "Hello there"])
    assert_equal("Hello there\n", result.output)
