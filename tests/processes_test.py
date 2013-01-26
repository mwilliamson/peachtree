from nose.tools import istest, assert_equal

from peachtree import processes, wait


@istest
def can_detect_if_process_is_running():
    process_set = processes.start({
        "sleep": ["sh", "-c", "sleep 0.1"]
    })
    assert process_set.all_running()
    wait.wait_until_not(process_set.all_running, timeout=1, wait_time=0.1)
    assert not process_set.all_running()


@istest
def output_of_each_process_is_labelled_by_process_alphabetically():
    process_set = processes.start({
        "true": ["true"],
        "false": ["false"]
    })
    wait.wait_until_not(process_set.all_running, timeout=1, wait_time=0.1)
    assert_equal("false:\ntrue:\n", process_set.all_output())


@istest
def output_of_each_process_is_indented():
    process_set = processes.start({
        "echo": ["sh", "-c", "echo one; echo two"]
    })
    wait.wait_until_not(process_set.all_running, timeout=1, wait_time=0.1)
    assert_equal("echo:\n    one\n    two\n", process_set.all_output())
    
    
@istest
def stderr_output_of_process_is_logged_with_normal_output():
    process_set = processes.start({
        "echo": ["sh", "-c", "echo hello 1>&2"]
    })
    wait.wait_until_not(process_set.all_running, timeout=1, wait_time=0.1)
    assert_equal("echo:\n    hello\n", process_set.all_output())
    

@istest
def can_kill_all_processes():
    process_set = processes.start({
        "one": ["sh", "-c", "sleep 1"],
        "two": ["sh", "-c", "sleep 1"],
    })
    
    assert process_set.all_running()
    process_set.kill_all()
    assert not process_set.any_running()


@istest
def can_kill_all_processes_after_restoring_process_set_from_run_dir():
    original_process_set = processes.start({
        "one": ["sh", "-c", "sleep 1"],
        "two": ["sh", "-c", "sleep 1"],
    })
    
    process_set = processes.from_dir(original_process_set.run_dir)
    
    assert process_set.all_running()
    process_set.kill_all()
    assert not process_set.any_running()
