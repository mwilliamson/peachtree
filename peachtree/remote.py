import requests

from . import sshconfig


def remote_provider(url=None, hostname=None, port=None):
    if url is None:
        if hostname is not None and port is not None:
            url = "http://{0}:{1}/".format(hostname, port)
        else:
            raise TypeError("Must provider url or hostname and port")
    return RemoteProvider(url)


class RemoteProvider(object):
    def __init__(self, base_url):
        self._api = RemoteApi(base_url)
        
    def start(self, image_name, public_ports=None):
        data = {"image-name": image_name, "public-ports": public_ports}
        response = self._api.start(image_name, public_ports=public_ports)
        return RemoteMachine(response, self._api)

    def find_running_machine(self, identifier):
        response = self._api.running_machine(identifier)
        return RemoteMachine(response, self._api)

    def _url(self, path):
        return "{0}/{1}".format(self._base_url.rstrip("/"), path.lstrip("/"))
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass


class RemoteMachine(object):
    def __init__(self, desc, api):
        self.identifier = desc["identifier"]
        self._ssh_config = sshconfig.from_dict(desc["sshConfig"])
        self._root_ssh_config = sshconfig.from_dict(desc["rootSshConfig"])
        self._api = api
    
    def ssh_config(self):
        return self._ssh_config
    
    def shell(self):
        return self._ssh_config.shell()
        
    def root_shell(self):
        return self._root_ssh_config.shell()
    
    def is_running(self):
        return self._api.is_running(self.identifier)
    
    def public_port(self, guest_port):
        return self._api.public_port(self.identifier, guest_port)
    
    def destroy(self):
        self._api.destroy(self.identifier)
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.destroy()


class RemoteApi(object):
    _action_timeout = 60
    _info_timeout = 10
    
    def __init__(self, base_url):
        self._base_url = base_url
        
    def start(self, image_name, public_ports=None):
        data = {
            "image-name": image_name,
            "public-ports": ",".join(map(str, public_ports or []))
        }
        return self._post(
            "start",
            data=data,
            timeout=self._action_timeout
        )
        
    def running_machine(self, identifier):
        return self._post(
            "running-machine",
            data={"identifier": identifier},
            timeout=self._info_timeout
        )
        
    def is_running(self, identifier):
        return self._post(
            "is-running",
            data={"identifier": identifier},
            timeout=self._info_timeout
        )["isRunning"]
        
    def public_port(self, identifier, port):
        return self._post(
            "public-port",
            data={"identifier": identifier, "guest-port": port},
            timeout=self._info_timeout
        )["port"]
        
    def destroy(self, identifier):
        return self._post(
            "destroy",
            data={"identifier": identifier},
            timeout=self._action_timeout,
        )

    def _post(self, path, data, timeout):
        response = requests.post(
            self._url(path),
            data=data,
            timeout=timeout
        )
        if response.status_code != 200:
            raise RuntimeError("Got response: {0}", response)
        content_type = response.headers["content-type"]
        return response.json()
        

    def _url(self, path):
        return "{0}/{1}".format(self._base_url.rstrip("/"), path.lstrip("/"))
        
