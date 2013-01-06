import time


def wait_until_not(predicate, *args, **kwargs):
    return wait_until(lambda: not predicate(), *args, **kwargs)

    
def wait_until(predicate, timeout, wait_time=None, message=None):
    start_time = time.time()
    timeout = 10
    wait_time = 0.1
    while not predicate():
        if time.time() - start_time > timeout:
            message = "Timeout expired" if message is None else message
            raise RuntimeError(message)
        time.sleep(wait_time)
