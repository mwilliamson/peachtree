import threading
import json
import functools
import SocketServer
from wsgiref.simple_server import make_server, WSGIServer

from pyramid.config import Configurator
from pyramid.response import Response

from . import dictobj
from .request import MachineRequest


_default_timeout = 60 * 60


def start_server(port, provider):
    def http_post(func):
        return view(func, "POST")
        
    def http_get(func):
        return view(func, "GET")
    
    
    def view(func, http_method):
        @functools.wraps(func)
        def respond(request):
            if request.method == http_method:
                # TODO: check some credentials
                status_code, result = func(request.json_body, **request.matchdict)
            else:
                status_code, result = 405, "{0} required".format(http_method)
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
        
    def machines(request):
        if request.method == "POST":
            return start(request)
        else:
            return running_machines(request)
    
    @http_post
    def start(body):
        machine_request = dictobj.dict_to_obj(body, MachineRequest)
        machine = provider.start(machine_request)
        return success(_describe_machine(machine))
            
    @http_get
    def running_machines(post):
        machines = provider.list_running_machines()
        return success(map(_describe_machine, machines))
        
    @http_get
    def running_machine(post, identifier):
        machine = provider.find_running_machine(identifier)
        if machine is None:
            return not_found(None)
        else:
            return success(_describe_machine(machine))
    
    @http_get
    def is_running(post, identifier):
        machine = provider.find_running_machine(identifier)
        is_running = machine is not None
        return success({"isRunning": is_running})
    
    @http_get
    def public_port(post, identifier):
        machine = provider.find_running_machine(identifier)
        if machine is None:
            return not_found(None)
        else:
            guest_port = int(post.get("guest-port"))
            public_port = machine.public_port(guest_port)
            return success({"port": public_port})
        
    @http_post
    def restart(post, identifier):
        machine = provider.find_running_machine(identifier)
        if machine is None:
            return not_found(None)
        else:
            machine.restart()
            return success({"status": "OK"})
        
    @http_post
    def destroy(post, identifier):
        machine = provider.find_running_machine(identifier)
        if machine is not None:
            machine.destroy()
        return success({"status": "OK"})
    
    def _describe_machine(machine):
        return {
            "identifier": machine.identifier,
            "name": machine.name,
            "imageName": machine.image_name,
            "hostname": machine.hostname(),
            "users": map(dictobj.obj_to_dict, machine.users()),
        }
    
    config = Configurator()
    
    config.add_route('machines', '/machines')
    config.add_view(machines, route_name='machines')
    
    def add_machine_route(path, view):
        name = path.replace("-", "_")
        path_suffix = "/" + path if path else ""
        config.add_route(name, '/machines/{identifier}' + path_suffix)
        config.add_view(view, route_name=name)
    
    add_machine_route("", running_machine)
    add_machine_route("is-running", is_running)
    add_machine_route("public-port", public_port)
    add_machine_route("restart", restart)
    add_machine_route("destroy", destroy)
    
    app = config.make_wsgi_app()
    
    server = make_server('0.0.0.0', port, app, ThreadedWSGIServer)
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

class ThreadedWSGIServer(SocketServer.ThreadingMixIn, WSGIServer):
     pass 
