import threading
import json
import functools

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.httpexceptions import HTTPNotFound

from . import sshconfig


_default_timeout = 60 * 60


def start_server(port, provider):
    def view(func):
        @functools.wraps(func)
        def respond(request):
            if request.method == "POST":
                # TODO: check some credentials
                result_dict = func(request.POST)
                return Response(json.dumps(result_dict), content_type="application/json")
                
        return respond
    
    @view
    def start(post):
        image_name = post.get("image-name")
        machine = provider.start(image_name, timeout=_default_timeout)
        ssh_config = machine.ssh_config()
        root_ssh_config = machine.ssh_config("root")
        
        return {
            "identifier": machine.identifier,
            "sshConfig": sshconfig.to_dict(ssh_config),
            "rootSshConfig": sshconfig.to_dict(root_ssh_config),
        }
    
    @view
    def is_running(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        is_running = machine is not None
        return {"isRunning": is_running}
        
    @view
    def destroy(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        if machine is not None:
            machine.destroy()
        return {"status": "OK"}
        
    
    config = Configurator()
    
    config.add_route('start', '/start')
    config.add_view(start, route_name='start')
    config.add_route('is_running', '/is-running')
    config.add_view(is_running, route_name='is_running')
    config.add_route('destroy', '/destroy')
    config.add_view(destroy, route_name='destroy')
    
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
