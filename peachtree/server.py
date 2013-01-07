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
        public_ports = [
            int(port)
            for port in post.get("public-ports").split(",")
            if port
        ]
        machine = provider.start(
            image_name,
            public_ports=public_ports,
            timeout=_default_timeout
        )
        return _describe_machine(machine)
        
    @view
    def running_machine(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        if machine is None:
            return None
        else:
            return _describe_machine(machine)
    
    @view
    def is_running(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        is_running = machine is not None
        return {"isRunning": is_running}
    
    @view
    def public_port(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        guest_port = int(post.get("guest-port"))
        public_port = machine.public_port(guest_port)
        return {"port": public_port}
        
    @view
    def restart(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        machine.restart()
        return {"status": "OK"}
        
    @view
    def destroy(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        if machine is not None:
            machine.destroy()
        return {"status": "OK"}
    
    def _describe_machine(machine):
        ssh_config = machine.ssh_config()
        root_ssh_config = machine.ssh_config("root")
        
        return {
            "identifier": machine.identifier,
            "sshConfig": sshconfig.to_dict(ssh_config),
            "rootSshConfig": sshconfig.to_dict(root_ssh_config),
        }
    
    config = Configurator()
    
    config.add_route('start', '/start')
    config.add_view(start, route_name='start')
    config.add_route('running_machine', '/running-machine')
    config.add_view(running_machine, route_name='running_machine')
    config.add_route('is_running', '/is-running')
    config.add_view(is_running, route_name='is_running')
    config.add_route('public_port', '/public-port')
    config.add_view(public_port, route_name='public_port')
    config.add_route('restart', '/restart')
    config.add_view(restart, route_name='restart')
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
