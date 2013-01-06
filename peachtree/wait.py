import time
import sys

    
def wait_until(predicate, *args, **kwargs):
    error_message = kwargs.pop("error_message", "Timeout expired")
    
    def on_error(result):
        raise RuntimeError(error_message)
    
    def condition():
        result = predicate()
        return result, result
    
    return _wait(condition, *args, on_error=on_error, **kwargs)


def wait_until_not(predicate, *args, **kwargs):
    return wait_until(lambda: not predicate(), *args, **kwargs)


def wait_until_successful(predicate, errors, *args, **kwargs):
    def try_predicate():
        try:
            return True, predicate()
        except errors:
            return False, sys.exc_info()
    
    def on_error(last_exception):
        raise last_exception[0], last_exception[1], last_exception[2]
    
    return _wait(try_predicate, *args, on_error=on_error, **kwargs)


def _wait(condition, timeout, wait_time=None, on_error=None):
    start_time = time.time()
    while True:
        finished, result = condition()
        if finished:
            return result
            
        if time.time() - start_time > timeout:
            return on_error(result)
            
        time.sleep(wait_time)
