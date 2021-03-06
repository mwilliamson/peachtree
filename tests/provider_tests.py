from nose.tools import assert_equals, assert_equal
import hamcrest
from hamcrest import assert_that, contains, has_property

from nose_test_sets import TestSetBuilder
from peachtree import wait
import peachtree


suite_builder = TestSetBuilder()
test = suite_builder.add_test


_IMAGE_NAME="ubuntu-precise-amd64"
_WINDOWS_IMAGE_NAME="windows-server-2012-x86-64"


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
def external_hostname_is_not_local(provider):
    with provider.start(_IMAGE_NAME) as machine:
        hostname = machine.external_hostname()
        assert_that(hostname, hamcrest.is_not(hamcrest.equal_to("localhost")))
        assert_that(hostname, hamcrest.is_not(hamcrest.starts_with("127")))


@test
def machine_can_resolve_its_own_internal_name(provider):
    with provider.start(_IMAGE_NAME) as machine:
        machine.shell().run(["ping", machine.name, "-c1"])
        
        
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


@test
def find_running_machine_returns_none_if_there_is_no_such_machine(provider):
    assert provider.find_running_machine("wonderful") is None


@test
def find_running_machine_returns_none_if_the_machine_has_been_shutdown(provider):
    with provider.start(_IMAGE_NAME) as machine:
        assert machine.is_running()
        machine.root_shell().run(["shutdown", "-h", "now"])
        
        wait.wait_until_not(machine.is_running, timeout=10, wait_time=0.1)
        
        assert provider.find_running_machine(machine.identifier) is None


@test
def can_run_commands_against_machine_found_using_identifier(provider):
    with provider.start(_IMAGE_NAME) as original_machine:
        identifier = original_machine.identifier
        
        machine = provider.find_running_machine(identifier)
        result = machine.shell().run(["echo", "Hello there"])
        assert_equals("Hello there\n", result.output)
        
        
@test
def can_restart_machine(provider):
    with provider.start(_IMAGE_NAME) as machine:
        machine.shell().run(["touch", "/tmp/hello"])
        machine.restart()
        
        result = machine.shell().run(["test", "-f", "/tmp/hello"], allow_error=True)
        assert_equals(1, result.return_code)



@test
def list_of_machines_is_empty_if_none_are_running(provider):
    assert_equals([], provider.list_running_machines())


@test
def list_of_machines_include_ids(provider):
    with provider.start(_IMAGE_NAME) as original_machine:
        running_machines = provider.list_running_machines()
        assert_that(
            running_machines,
            contains(has_property("identifier", original_machine.identifier))
        )

@test
def list_of_machines_include_image_name(provider):
    with provider.start(_IMAGE_NAME):
        running_machines = provider.list_running_machines()
        assert_that(
            running_machines,
            contains(has_property("image_name", _IMAGE_NAME))
        )

@test
def machines_that_have_stopped_are_not_in_list_of_running_machines(provider):
    with provider.start(_IMAGE_NAME):
        pass
    running_machines = provider.list_running_machines()
    assert_equals([], running_machines)


@test
def can_start_multiple_machines(provider):
    requests = [
        peachtree.request_machine("first", image_name=_IMAGE_NAME),
        peachtree.request_machine("second", image_name=_IMAGE_NAME),
    ]
    with provider.start_many(requests) as machines:
        _assert_can_run_commands_on_machine(machines[0])
        _assert_can_run_commands_on_machine(machines[1])
        _assert_can_run_commands_on_machine(machines["first"])
        _assert_can_run_commands_on_machine(machines["second"])


@test
def list_of_images_is_list_of_image_names(provider):
    assert_equals([_IMAGE_NAME, _WINDOWS_IMAGE_NAME], provider.list_images())


def _assert_can_run_commands_on_machine(machine):
    shell = machine.shell()
    result = shell.run(["echo", "Hello there"])
    assert_equal("Hello there\n", result.output)

    
create = suite_builder.create    
