import json
import sys

from peachtree import human


def find_writer_by_name(name, output_file=None):
    if output_file is None:
        output_file = sys.stdout
        
    return _writers[name](output_file)
    
    
def writer_names():
    return _writers.keys()


class JsonWriter(object):
    def __init__(self, output_file):
        self._output_file = output_file
    
    def write_result(self, value):
        self._output_file.write(json.dumps(value, indent=4, separators=(',',':')))
        self._output_file.write("\n")


class HumanWriter(object):
    def __init__(self, output_file):
        self._output_file = output_file
    
    def write_result(self, value):
        self._output_file.write(human.dumps(value))


_writers = {
    "json": JsonWriter,
    "human": HumanWriter,
}
