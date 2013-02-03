import requests
import urllib
import json

from .machines import MachineWrapper
from . import dictobj
from .users import User
from .request import request_machine, MachineRequest


def remote_provider(url=None, hostname=None, port=None):
    if url is None:
        if hostname is not None and port is not None:
            url = "http://{0}:{1}/".format(hostname, port)
        else:
            raise TypeError("Must provide either: url, or; hostname and port")
    return RemoteProvider(url)


class RemoteProvider(object):
    def __init__(self, base_url):
        self._api = RemoteApi(base_url)
        
    def start(self, *args, **kwargs):
        # TODO: remove duplication with QemuProvider.start
        if len(args) == 1 and not kwargs and isinstance(args[0], MachineRequest):
            request = args[0]
        else:
            request = request_machine(*(["peachtree"] + list(args)), **kwargs)
        response = self._api.start(request)
        return _create_machine(response, self._api)

    def find_running_machine(self, identifier):
        response = self._api.running_machine(identifier)
        if response is None:
            return None
        else:
            return _create_machine(response, self._api)
    
    def list_running_machines(self):
        machines = self._api.running_machines()
        return [_create_machine(machine, self._api) for machine in machines]
    
    def _url(self, path):
        return "{0}/{1}".format(self._base_url.rstrip("/"), path.lstrip("/"))
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass


def _create_machine(*args, **kwargs):
    return MachineWrapper(RemoteMachine(*args, **kwargs))


class RemoteMachine(object):
    def __init__(self, desc, api):
        self.identifier = desc["identifier"]
        self.name = desc["name"]
        self.image_name = desc["imageName"]
        self._hostname = desc["hostname"]
        self._users = [dictobj.dict_to_obj(user, User) for user in desc["users"]]
        self._api = api
    
    def hostname(self):
        return self._hostname
        
    def users(self):
        return self._users
    
    def is_running(self):
        return self._api.is_running(self.identifier)
    
    def public_port(self, guest_port):
        return self._api.public_port(self.identifier, guest_port)
    
    def restart(self):
        return self._api.restart(self.identifier)
    
    def destroy(self):
        self._api.destroy(self.identifier)
    
    def __repr__(self):
        return "RemoteMachine {0}".format(self.identifier)


class RemoteApi(object):
    _action_timeout = 60
    _info_timeout = 10
    
    def __init__(self, base_url):
        self._base_url = base_url
        
    def start(self, request):
        return self._action(
            "machines",
            data=dictobj.obj_to_dict(request),
        )
        
    def running_machine(self, identifier):
        return self._info(self._machine_path(identifier))
        
    def running_machines(self):
        return self._info("machines", data=None)
        
    def is_running(self, identifier):
        response = self._info(self._machine_path(identifier, "is-running"))
        return response["isRunning"]
        
    def public_port(self, identifier, port):
        return self._info(
            self._machine_path(identifier, "public-port"),
            data={"guest-port": port},
        )["port"]
        
    def restart(self, identifier):
        self._action(self._machine_path(identifier, "restart"))
        
    def destroy(self, identifier):
        self._action(self._machine_path(identifier, "destroy"))

    def _action(self, *args, **kwargs):
        return self._request(
            "POST", *args, timeout=self._action_timeout, **kwargs)
        
    def _info(self, *args, **kwargs):
        return self._request(
            "GET", *args, timeout=self._info_timeout, **kwargs)

    def _request(self, method, path, timeout, data=None):
        response = requests.request(
            method,
            self._url(path),
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        if response.status_code not in [200, 404]:
            raise RuntimeError("Got response: {0}", response)
        return response.json()
        

    def _url(self, path):
        return "{0}/{1}".format(self._base_url.rstrip("/"), path.lstrip("/"))
        
    def _machine_path(self, identifier, extra=None):
        path = "machines/{0}".format(urllib.quote(identifier))
        if extra is None:
            return path
        else:
            return "{0}/{1}".format(path, extra)
        
