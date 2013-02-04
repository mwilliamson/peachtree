import time

from nose.tools import istest, assert_equal, assert_raises

from peachtree import futures


@istest
def thread_map_across_empty_list_returns_empty_iterator():
    result = futures.thread_map(lambda x: x, [])
    assert_equal(0, len(result))


@istest
def passing_identity_function_to_thread_map_preserves_elements():
    original = ["apple", "banana", "coconut"]
    result = futures.thread_map(lambda x: x, original)
    assert_equal(original, list(result))


@istest
def thread_map_applies_function_to_each_element():
    original = [1, 2, 3]
    result = futures.thread_map(lambda x: x * x, original)
    assert_equal([1, 4, 9], list(result))


@istest
def thread_map_preserves_order_of_elements():
    original = [0.1, 0.05, 0]
    
    def waiting_identity(value):
        time.sleep(value)
        return value
    
    result = futures.thread_map(waiting_identity, original)
    assert_equal(original, list(result))


@istest
def error_is_raised_if_mapping_function_raises_error():
    class KurtError(Exception):
        pass
    
    def raise_error(value):
        raise KurtError("No, Javier, No!")
    
    assert_raises(KurtError, lambda: futures.thread_map(raise_error, [0]))

