import uuid
import functools
import os

from nose.tools import istest, nottest, assert_equal, assert_raises
import spur

from peachtree import processes, wait
from .tempdir import create_temporary_dir


@nottest
def test(func):
    @functools.wraps(func)
    def run_test():
        with create_temporary_dir() as temp_dir:
            def start(commands):
                run_dir = os.path.join(temp_dir, str(uuid.uuid4()))
                return processes.start(commands, run_dir)
            
            return func(start)
    
    return istest(run_test)


@test
def can_detect_if_process_is_running(start):
    process_set = start({
        "sleep": ["sh", "-c", "sleep 0.1"]
    })
    assert process_set.all_running()
    wait.wait_until_not(process_set.all_running, timeout=1, wait_time=0.1)
    assert not process_set.all_running()


@test
def output_of_each_process_is_labelled_by_process_alphabetically(start):
    process_set = start({
        "true": ["true"],
        "false": ["false"]
    })
    wait.wait_until_not(process_set.all_running, timeout=1, wait_time=0.1)
    assert_equal("false:\ntrue:\n", process_set.all_output())


@test
def output_of_each_process_is_indented(start):
    process_set = start({
        "echo": ["sh", "-c", "echo one; echo two"]
    })
    wait.wait_until_not(process_set.all_running, timeout=1, wait_time=0.1)
    assert_equal("echo:\n    one\n    two\n", process_set.all_output())
    
    
@test
def stderr_output_of_process_is_logged_with_normal_output(start):
    process_set = start({
        "echo": ["sh", "-c", "echo hello 1>&2"]
    })
    wait.wait_until_not(process_set.all_running, timeout=1, wait_time=0.1)
    assert_equal("echo:\n    hello\n", process_set.all_output())
    

@test
def can_kill_all_processes(start):
    process_set = start({
        "one": ["sh", "-c", "sleep 1"],
        "two": ["sh", "-c", "sleep 1"],
    })
    
    assert process_set.all_running()
    process_set.kill_all()
    assert not process_set.any_running()
    

@test
def kill_all_kills_process(start):
    identifier = str(uuid.uuid4())
    process_set = start({
        "one": ["sh", "-c", "cat; echo {0}".format(identifier)],
    })
    
    def process_is_running():
        result = spur.LocalShell().run(["pgrep", "-f", identifier], allow_error=True)
        if result.return_code == 0:
            return True
        elif result.return_code == 1:
            return False
        else:
            raise result.to_error()
    
    wait.wait_until(process_is_running, timeout=1, wait_time=0.1)
    assert process_is_running()
    process_set.kill_all()
    wait.wait_until_not(process_is_running, timeout=1, wait_time=0.1)
    assert not process_is_running()


@test
def can_kill_all_processes_after_restoring_process_set_from_run_dir(start):
    original_process_set = start({
        "one": ["sh", "-c", "sleep 1"],
        "two": ["sh", "-c", "sleep 1"],
    })
    
    process_set = processes.from_dir(original_process_set.run_dir)
    
    assert process_set.all_running()
    process_set.kill_all()
    assert not process_set.any_running()


@test
def additional_processes_can_be_started(start):
    process_set = start({})
    assert not process_set.any_running()
    process_set.start({
        "sleep": ["sh", "-c", "sleep 0.1"]
    })
    assert process_set.any_running()
    wait.wait_until_not(process_set.any_running, timeout=1, wait_time=0.1)
    assert not process_set.any_running()


@test
def additional_processes_can_be_started_and_restored_from_run_dir(start):
    original_process_set = start({
        "true1": ["true"],
    })
    original_process_set.start({
        "true2": ["true"]
    })
    process_set = processes.from_dir(original_process_set.run_dir)
    assert_equal("true1:\ntrue2:\n", process_set.all_output())


@test
def error_is_raised_if_trying_to_start_process_with_duplicate_name(start):
    process_set = start({"true": ["true"]})
    assert_raises(ValueError, lambda: process_set.start({"true": ["true"]}))
