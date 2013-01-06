import os
import contextlib

from nose.tools import istest, assert_equals
from hamcrest import assert_that, contains, has_property
import spur

import peachtree
import peachtree.qemu

from .tempdir import create_temporary_dir
from peachtree import wait

import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


_IMAGE_NAME="ubuntu-precise-amd64"


qemu_provider = peachtree.qemu_provider()

@istest
def can_run_commands_on_vm():
    with qemu_provider.start(_IMAGE_NAME) as vm:
        shell = vm.shell()
        result = shell.run(["echo", "Hello there"])
        assert_equals("Hello there\n", result.output)


@istest
def can_ensure_that_ports_are_available():
    with qemu_provider.start(_IMAGE_NAME, public_ports=[50022]) as vm:
        root_shell = vm.root_shell()
        root_shell.run(["sh", "-c", "echo Port 50022 >> /etc/ssh/sshd_config"])
        root_shell.run(["service", "ssh", "restart"])
        
        ssh_config = vm.ssh_config()
        ssh_config.port = vm.public_port(50022)
        shell = ssh_config.shell()
        result = shell.run(["echo", "Hello there"])
        assert_equals("Hello there\n", result.output)


@istest
def can_restart_vm():
    with qemu_provider.start(_IMAGE_NAME) as vm:
        vm.shell().run(["touch", "/tmp/hello"])
        vm.restart()
        
        result = vm.shell().run(["test", "-f", "/tmp/hello"], allow_error=True)
        assert_equals(1, result.return_code)
        
        
@istest
def machine_is_not_running_after_context_manager_for_machine_exits():
    with qemu_provider.start(_IMAGE_NAME) as machine:
        assert machine.is_running()
        
    assert not machine.is_running()
        
        
@istest
def can_find_running_machine_using_identifier_and_then_stop_vm():
    with qemu_provider.start(_IMAGE_NAME) as original_vm:
        identifier = original_vm.identifier
        
        vm = qemu_provider.find_running_machine(identifier)
        assert vm.is_running()
        vm.destroy()
        assert not vm.is_running()
        
@istest
def find_running_machine_returns_none_if_there_is_no_such_machine():
    assert qemu_provider.find_running_machine("wonderful") is None
        
@istest
def find_running_machine_returns_none_if_the_machine_has_been_shutdown():
    with qemu_provider.start(_IMAGE_NAME) as vm:
        def process_is_running():
            result = spur.LocalShell().run(
                ["pgrep", "-f", vm.identifier],
                allow_error=True
            )
            return result.return_code == 0
            
        assert process_is_running()
        vm.root_shell().run(["shutdown", "-h", "now"])
        
        wait.wait_until_not(process_is_running, timeout=10, wait_time=0.1)
        
        assert qemu_provider.find_running_machine(vm.identifier) is None

@istest
def can_run_commands_against_vm_found_using_identifier():
    with qemu_provider.start(_IMAGE_NAME) as original_vm:
        identifier = original_vm.identifier
        
        vm = qemu_provider.find_running_machine(identifier)
        result = vm.shell().run(["echo", "Hello there"])
        assert_equals("Hello there\n", result.output)

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


@contextlib.contextmanager
def provider_with_temp_data_dir():
    with create_temporary_dir() as data_dir:
        image_path = peachtree.qemu.Images().image_path(_IMAGE_NAME)
        temp_image_path = peachtree.qemu.Images(data_dir).image_path(_IMAGE_NAME)
        os.makedirs(os.path.dirname(temp_image_path))
        os.symlink(image_path, temp_image_path)
        
        yield peachtree.qemu_provider(data_dir=data_dir)
