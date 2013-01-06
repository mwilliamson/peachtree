from nose.tools import assert_equals

from .suite_builder import TestSuiteBuilder


suite_builder = TestSuiteBuilder()
test = suite_builder.add_test


_IMAGE_NAME="ubuntu-precise-amd64"


@test
def can_run_commands_on_vm(provider):
    with provider.start(_IMAGE_NAME) as machine:
        shell = machine.shell()
        result = shell.run(["echo", "Hello there"])
        assert_equals("Hello there\n", result.output)


@test
def machine_is_not_running_after_context_manager_for_machine_exits(provider):
    with provider.start(_IMAGE_NAME) as machine:
        assert machine.is_running()
    assert not machine.is_running()


create = suite_builder.create    
