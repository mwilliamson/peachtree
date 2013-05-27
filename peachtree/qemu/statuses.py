import os
import json
import errno

from .. import dictobj


class Statuses(object):
    def __init__(self, status_dir):
        self._status_dir = status_dir
        
    def remove(self, identifier):
        try:
            os.remove(self._status_path(identifier))
        except OSError as error:
            # ENOENT: Machine has been shut down in the interim, so ignore
            if error.errno != errno.ENOENT:
                raise
    
    def write(self, status):
        status_json = dictobj.obj_to_dict(status)
        self._write_json(status.identifier, status_json)
    
    def read(self, identifier):
        try:
            status_dict = self._read_json(identifier)
        except IOError as error:
            # ENOENT: Machine has been shut down in the interim, so ignore
            if error.errno == errno.ENOENT:
                return None
            else:
                raise
        
        status_dict["forwardedPorts"] = dict(
            (int(guest_port), host_port)
            for guest_port, host_port
            in status_dict["forwardedPorts"].iteritems()
        )
        status = dictobj.dict_to_obj(status_dict, MachineStatus)
        return status
                        
    def read_all(self):
        if not os.path.exists(self._status_dir):
            return []
        identifiers = os.listdir(self._status_dir)
        statuses = map(self.read, identifiers)
        return filter(lambda status: status is not None, statuses)
    
    def _status_path(self, identifier):
        return os.path.join(self._status_dir, identifier)

    def _read_json(self, identifier):
        status_file_path = self._status_path(identifier)
        with open(status_file_path) as status_file:
            return json.load(status_file)
    
    def _write_json(self, identifier, data):
        status_path = self._status_path(identifier)
        
        _mkdir_p(os.path.dirname(status_path))
            
        with open(status_path, "w") as status_file:
            json.dump(data, status_file)


MachineStatus = dictobj.data_class("MachineStatus",
    [
        "identifier",
        "name",
        "image_name",
        "ssh_internal_port",
        "forwarded_ports",
        "start_time",
        "timeout",
        "process_set_run_dir",
    ]
)


def _mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as error:
        if not (error.errno == errno.EEXIST and os.path.isdir(path)):
            raise
