import threading
import json
import functools

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response

from . import sshconfig


_default_timeout = 60 * 60


def start_server(port, provider):
    def view(func):
        @functools.wraps(func)
        def respond(request):
            if request.method == "POST":
                # TODO: check some credentials
                status_code, result = func(request.POST)
            else:
                status_code, result = 405, "POST required"
            return Response(
                json.dumps(result),
                status_code=status_code,
                content_type="application/json"
            )
                
        return respond
    
    def success(result):
        return 200, result
        
    def not_found(result):
        return 404, result
    
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
        return success(_describe_machine(machine))
        
    @view
    def running_machine(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        if machine is None:
            return not_found(None)
        else:
            return success(_describe_machine(machine))
            
    @view
    def running_machines(post):
        machines = provider.list_running_machines()
        return success(map(_describe_machine, machines))
    
    @view
    def is_running(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        is_running = machine is not None
        return success({"isRunning": is_running})
    
    @view
    def public_port(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        if machine is None:
            return not_found(None)
        else:
            guest_port = int(post.get("guest-port"))
            public_port = machine.public_port(guest_port)
            return success({"port": public_port})
        
    @view
    def restart(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        if machine is None:
            return not_found(None)
        else:
            machine.restart()
            return success({"status": "OK"})
        
    @view
    def destroy(post):
        identifier = post.get("identifier")
        machine = provider.find_running_machine(identifier)
        if machine is not None:
            machine.destroy()
        return success({"status": "OK"})
    
    def _describe_machine(machine):
        ssh_config = machine.ssh_config()
        root_ssh_config = machine.ssh_config("root")
        
        return {
            "identifier": machine.identifier,
            "imageName": machine.image_name,
            "sshConfig": sshconfig.to_dict(ssh_config),
            "rootSshConfig": sshconfig.to_dict(root_ssh_config),
        }
    
    config = Configurator()
    
    config.add_route('start', '/start')
    config.add_view(start, route_name='start')
    config.add_route('running_machine', '/running-machine')
    config.add_view(running_machine, route_name='running_machine')
    config.add_route('running_machines', '/running-machines')
    config.add_view(running_machines, route_name='running_machines')
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
    
    return Server(server, server_thread, provider)


class Server(object):
    def __init__(self, server, thread, provider):
        self._server = server
        self._thread = thread
        self._provider = provider
    
    def cron(self):
        if hasattr(self._provider, "cron"):
            self._provider.cron()
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self._server.shutdown()
        self._thread.join()
