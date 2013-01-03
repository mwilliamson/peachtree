from nose.tools import istest, assert_equals

import peachtree

@istest
def can_run_commands_on_vm():
    with peachtree.start_kvm("ubuntu-precise-amd64") as vm:
        shell = vm.shell()
        result = shell.run(["echo", "Hello there"])
        assert_equals("Hello there\n", result.output)
