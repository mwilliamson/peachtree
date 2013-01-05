from nose.tools import istest, assert_equals

import peachtree


import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


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
def can_find_running_vm_using_identifier_and_then_stop_vm():
    with peachtree.start_kvm("ubuntu-precise-amd64") as original_vm:
        vm_id = original_vm.vm_id
        
        vm = peachtree.find_running_vm(vm_id)
        assert vm.is_running()
        vm.destroy()
        assert not vm.is_running()

