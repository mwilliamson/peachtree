import os
import contextlib

from nose.tools import istest, assert_equals
from hamcrest import assert_that, contains, has_property, is_not
import spur

import peachtree
import peachtree.qemu

from .tempdir import create_temporary_dir

import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


_IMAGE_NAME="ubuntu-precise-amd64"

@istest
def can_run_commands_on_vm():
    with peachtree.start_kvm("ubuntu-precise-amd64") as vm:
        shell = vm.shell()
        result = shell.run(["echo", "Hello there"])
        assert_equals("Hello there\n", result.output)


@istest
def can_ensure_that_ports_are_available():
    with peachtree.start_kvm("ubuntu-precise-amd64", public_ports=[50022]) as vm:
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
    with peachtree.start_kvm("ubuntu-precise-amd64") as vm:
        vm.shell().run(["touch", "/tmp/hello"])
        vm.restart()
        
        result = vm.shell().run(["test", "-f", "/tmp/hello"], allow_error=True)
        assert_equals(1, result.return_code)
        
@istest
def can_detect_if_vm_is_running():
    with peachtree.start_kvm("ubuntu-precise-amd64") as vm:
        assert vm.is_running()
        
    assert not vm.is_running()
        
        
@istest
def can_find_running_machine_using_identifier_and_then_stop_vm():
    with peachtree.start_kvm("ubuntu-precise-amd64") as original_vm:
        identifier = original_vm.identifier
        
        vm = peachtree.find_running_machine(identifier)
        assert vm.is_running()
        vm.destroy()
        assert not vm.is_running()
        
@istest
def error_is_raised_if_identifier_is_invalid():
    try:
        peachtree.find_running_machine("wonderful")
        raise AssertionError("Expected error")
    except RuntimeError as error:
        assert_equals('Could not find running VM with id "wonderful"', error.message)
        
@istest
def error_is_raised_if_vm_with_id_is_not_running():
    with peachtree.start_kvm("ubuntu-precise-amd64") as vm:
        # Yes, this is a bit evil
        spur.LocalShell().run(["pkill", "-f", vm.identifier])
        
        try:
            peachtree.find_running_machine(vm.identifier)
            raise AssertionError("Expected error")
        except RuntimeError as error:
            assert error.message.startswith('Could not find running VM with id')

@istest
def can_run_commands_against_vm_found_using_identifier():
    with peachtree.start_kvm("ubuntu-precise-amd64") as original_vm:
        identifier = original_vm.identifier
        
        vm = peachtree.find_running_machine(identifier)
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
            assert_that(running_machines, contains(has_property("identifier", original_vm.identifier)))
            
@istest
def machines_that_have_stopped_are_not_in_list_of_running_machines():
    with provider_with_temp_data_dir() as provider:
        with provider.start(_IMAGE_NAME) as original_vm:
            pass
        running_machines = provider.list_running_machines()
        assert_equals([], running_machines)



@contextlib.contextmanager
def provider_with_temp_data_dir():
    with create_temporary_dir() as data_dir:
        provider = peachtree.qemu.QemuProvider(data_dir=data_dir)
        image_path = peachtree.qemu.QemuProvider().image_path(_IMAGE_NAME)
        temp_image_path = provider.image_path(_IMAGE_NAME)
        os.makedirs(os.path.dirname(temp_image_path))
        os.symlink(image_path, temp_image_path)
        yield provider
