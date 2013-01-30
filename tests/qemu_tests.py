import os
import contextlib

from nose.tools import istest

import peachtree
import peachtree.qemu

from .tempdir import create_temporary_dir
from . import provider_tests

import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


_IMAGE_NAME="ubuntu-precise-amd64"


@contextlib.contextmanager
def provider_with_temp_data_dir(networking):
    with create_temporary_dir() as data_dir:
        image_path = peachtree.qemu.Images().image_path(_IMAGE_NAME)
        temp_image_path = peachtree.qemu.Images(data_dir).image_path(_IMAGE_NAME)
        os.makedirs(os.path.dirname(temp_image_path))
        os.symlink(image_path, temp_image_path)
        
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

