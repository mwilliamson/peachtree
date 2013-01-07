import os
import contextlib

from nose.tools import istest, assert_equals
from hamcrest import assert_that, contains, has_property
import spur

import peachtree
import peachtree.qemu

from .tempdir import create_temporary_dir
from peachtree import wait
from . import provider_tests

import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


_IMAGE_NAME="ubuntu-precise-amd64"


qemu_provider = peachtree.qemu_provider()

@contextlib.contextmanager
def provider_with_temp_data_dir():
    with create_temporary_dir() as data_dir:
        image_path = peachtree.qemu.Images().image_path(_IMAGE_NAME)
        temp_image_path = peachtree.qemu.Images(data_dir).image_path(_IMAGE_NAME)
        os.makedirs(os.path.dirname(temp_image_path))
        os.symlink(image_path, temp_image_path)
        
        yield peachtree.qemu_provider(data_dir=data_dir)

QemuProviderTests = provider_tests.create(
    "QemuProviderTests",
    provider_with_temp_data_dir
)


@istest
def can_restart_vm():
    with qemu_provider.start(_IMAGE_NAME) as vm:
        vm.shell().run(["touch", "/tmp/hello"])
        vm.restart()
        
        result = vm.shell().run(["test", "-f", "/tmp/hello"], allow_error=True)
        assert_equals(1, result.return_code)

@istest
def list_of_machines_is_empty_if_none_are_running():
    with provider_with_temp_data_dir() as provider:
        assert_equals([], provider.list_running_machines())

@istest
def list_of_machines_include_ids():
    with provider_with_temp_data_dir() as provider:
        with provider.start(_IMAGE_NAME) as original_vm:
            running_machines = provider.list_running_machines()
            assert_that(
                running_machines,
                contains(has_property("identifier", original_vm.identifier))
            )
            
@istest
def list_of_machines_include_image_name():
    with provider_with_temp_data_dir() as provider:
        with provider.start(_IMAGE_NAME):
            running_machines = provider.list_running_machines()
            assert_that(
                running_machines,
                contains(has_property("image_name", _IMAGE_NAME))
            )
            
@istest
def machines_that_have_stopped_are_not_in_list_of_running_machines():
    with provider_with_temp_data_dir() as provider:
        with provider.start(_IMAGE_NAME):
            pass
        running_machines = provider.list_running_machines()
        assert_equals([], running_machines)
        
@istest
def running_cron_kills_any_running_machines_past_timeout():
    with qemu_provider.start(_IMAGE_NAME, timeout=0) as machine:
        qemu_provider.cron()
        assert not machine.is_running()
        
@istest
def cron_does_not_kill_machines_without_timeout():
    with qemu_provider.start(_IMAGE_NAME) as machine:
        qemu_provider.cron()
        assert machine.is_running()

