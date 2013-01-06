import functools
import contextlib

from nose.tools import istest, nottest


class TestSuiteBuilder(object):
    def __init__(self):
        self._test_funcs = []
    
    @nottest
    def add_test(self, func):
        self._test_funcs.append(func)
        
    def create(self, name, *arg_builders):
        @istest
        class Tests(object):
            pass
            
        for test_func in self._test_funcs:
            self._add_test_func(Tests, test_func, arg_builders)
        
        Tests.__name__ = name
        return Tests
        
    def _add_test_func(self, cls, test_func, arg_builders):
        @functools.wraps(test_func)
        @istest
        def run_test(self):
            # TODO: re-implement nested more robustly
            with contextlib.nested(*map(apply, arg_builders)) as args:
                test_func(*args)
        
        setattr(cls, test_func.__name__, run_test)
