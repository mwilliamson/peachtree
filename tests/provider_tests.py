from nose.tools import assert_equals

from .suite_builder import TestSuiteBuilder


suite_builder = TestSuiteBuilder()
test = suite_builder.add_test


_IMAGE_NAME="ubuntu-precise-amd64"


@test
def can_run_commands_on_machine(provider):
    with provider.start(_IMAGE_NAME) as machine:
        shell = machine.shell()
        result = shell.run(["echo", "Hello there"])
        assert_equals("Hello there\n", result.output)


@test
def can_run_commands_on_machine_as_root(provider):
    with provider.start(_IMAGE_NAME) as machine:
        shell = machine.root_shell()
        shell.run(["sh", "-c", "echo hello there > /root/hello"])
        result = shell.run(["cat", "/root/hello"])
        assert_equals("hello there\n", result.output)


@test
def machine_is_not_running_after_context_manager_for_machine_exits(provider):
    with provider.start(_IMAGE_NAME) as machine:
        assert machine.is_running()
    assert not machine.is_running()


@test
def can_ensure_that_ports_are_available(provider):
    with provider.start(_IMAGE_NAME, public_ports=[50022]) as vm:
        root_shell = vm.root_shell()
        root_shell.run(["sh", "-c", "echo Port 50022 >> /etc/ssh/sshd_config"])
        root_shell.run(["service", "ssh", "restart"])
        
        ssh_config = vm.ssh_config()
        ssh_config.port = vm.public_port(50022)
        assert ssh_config.port is not None
        shell = ssh_config.shell()
        result = shell.run(["echo", "Hello there"])
        assert_equals("Hello there\n", result.output)


@test
def can_find_running_machine_using_identifier_and_then_stop_machine(provider):
    with provider.start(_IMAGE_NAME) as original_machine:
        identifier = original_machine.identifier
        
        machine = provider.find_running_machine(identifier)
        assert machine.is_running()
        machine.destroy()
        assert not machine.is_running()


create = suite_builder.create    
