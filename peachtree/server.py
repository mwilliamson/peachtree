import threading
import json

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.httpexceptions import HTTPNotFound

from . import sshconfig


_default_timeout = 60 * 60


def start_server(port, provider):
    def start(request):
        if request.method == "POST":
            # TODO: check some credentials
            image_name = request.POST.get("image-name")
            machine = provider.start(image_name, timeout=_default_timeout)
            ssh_config = machine.ssh_config()
            
            desc = {
                "sshConfig": sshconfig.to_dict(ssh_config)
            }
            return Response(json.dumps(desc), content_type="application/json")
        
    
    config = Configurator()
    config.add_route('start', '/start')
    config.add_view(start, route_name='start')
    app = config.make_wsgi_app()
    
    server = make_server('0.0.0.0', port, app)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    
    return Server(server, server_thread)


class Server(object):
    def __init__(self, server, thread):
        self._server = server
        self._thread = thread
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self._server.shutdown()
        self._thread.join()
