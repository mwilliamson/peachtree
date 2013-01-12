import time

from nose.tools import assert_equals
import hamcrest
from hamcrest import assert_that, contains, has_property
import spur

from nose_test_sets import TestSetBuilder
from peachtree import wait


suite_builder = TestSetBuilder()
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


@test
def find_running_machine_returns_none_if_there_is_no_such_machine(provider):
    assert provider.find_running_machine("wonderful") is None


@test
def find_running_machine_returns_none_if_the_machine_has_been_shutdown(provider):
    with provider.start(_IMAGE_NAME) as machine:
        def process_is_running():
            result = spur.LocalShell().run(
                ["pgrep", "-f", machine.identifier],
                allow_error=True
            )
            return result.return_code == 0
            
        assert process_is_running()
        machine.root_shell().run(["shutdown", "-h", "now"])
        
        wait.wait_until_not(process_is_running, timeout=10, wait_time=0.1)
        
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
def list_of_machines_include_start_time(provider):
    request_time = time.time()
    with provider.start(_IMAGE_NAME):
        running_machines = provider.list_running_machines()
        start_time = hamcrest.all_of(
            hamcrest.greater_than_or_equal_to(request_time),
            hamcrest.less_than_or_equal_to(time.time())
        )
        assert_that(
            running_machines,
            contains(has_property("start_time", start_time))
        )

@test
def machines_that_have_stopped_are_not_in_list_of_running_machines(provider):
    with provider.start(_IMAGE_NAME):
        pass
    running_machines = provider.list_running_machines()
    assert_equals([], running_machines)


@test
def list_of_available_images_contains_images_that_can_be_started(provider):
    assert_equals([_IMAGE_NAME], provider.list_available_images())
    

create = suite_builder.create    
