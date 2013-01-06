import requests

from . import sshconfig


_start_timeout = 60


def remote_provider(url=None, hostname=None, port=None):
    if url is None:
        if hostname is not None and port is not None:
            url = "http://{0}:{1}/".format(hostname, port)
        else:
            raise TypeError("Must provider url or hostname and port")
    return RemoteProvider(url)


class RemoteProvider(object):
    def __init__(self, base_url):
        self._base_url = base_url
        
    def start(self, image_name):
        data = {"image-name": image_name}
        response = requests.post(
            self._url("start"),
            data=data,
            timeout=_start_timeout
        )
        if response.status_code != 200:
            raise RuntimeError("Got response: {0}", response)
        return RemoteMachine(response.json())

    def _url(self, path):
        return "{0}/{1}".format(self._base_url.rstrip("/"), path.lstrip("/"))
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass


class RemoteMachine(object):
    def __init__(self, desc):
        self._desc = desc
        
    def shell(self):
        return sshconfig.from_dict(self._desc["sshConfig"]).shell()
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass
