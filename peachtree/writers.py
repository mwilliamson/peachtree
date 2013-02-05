import json


def find_writer_by_name(name):
    return _writers[name]
    
def writer_names():
    return _writers.keys()


class JsonWriter(object):
    def write_result(self, value):
        print json.dumps(value, indent=4)


_writers = {
    "json": JsonWriter()
}
