import threading
import sys


def thread_map(func, iterable):
    workers = [start_worker(func, (value, )) for value in iterable]
    return [worker.join() for worker in workers]


def start_worker(func, args):
    worker = Worker(lambda: func(*args))
    worker.start()
    return worker
    

class Worker(object):
    def __init__(self, func):
        self._func = func
        self._error = None
        
    def start(self):
        self._thread = threading.Thread(target=self._apply)
        self._thread.start()
    
    def join(self):
        self._thread.join()
        if self._error is None:
            return self._value
        else:
            self._reraise_error()
    
    def _apply(self):
        try:
            self._value = self._func()
        except:
            self._error = sys.exc_info()
            raise
            
    def _reraise_error(self):
        raise self._error[0], self._error[1], self._error[2]
