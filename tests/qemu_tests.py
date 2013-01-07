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
def running_cron_kills_any_running_machines_past_timeout():
    with qemu_provider.start(_IMAGE_NAME, timeout=0) as machine:
        qemu_provider.cron()
        assert not machine.is_running()


@istest
def cron_does_not_kill_machines_without_timeout():
    with qemu_provider.start(_IMAGE_NAME) as machine:
        qemu_provider.cron()
        assert machine.is_running()

