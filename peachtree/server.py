import threading
import json
import functools
import SocketServer
from wsgiref.simple_server import make_server, WSGIServer

from pyramid.config import Configurator
from pyramid.response import Response

from . import dictobj
from .request import MachineRequest
from . import machine_description


_default_timeout = 60 * 60


def start_server(port, provider):
    def http_post(func):
        return view({"POST": func})
        
    def http_get(func):
        return view({"GET": func})
    
    
    def view(funcs):
        def respond(request):
            func = funcs.get(request.method, None)
            if func is None:
                http_methods = funcs.keys()
                message = "{0} required".format(" or ".join(http_methods))
                status_code, result = 405, message
            else:
                # TODO: check some credentials
                status_code, result = func(request.json_body, **request.matchdict)
                
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
        
    def start(body):
        if isinstance(body, list):
            machine_requests = [
                dictobj.dict_to_obj(request_dict, MachineRequest)
                for request_dict in body
            ]
            machine_set = provider.start_many(machine_requests)
            return success(map(_describe_machine, machine_set))
        else:
            machine_request = dictobj.dict_to_obj(body, MachineRequest)
            machine = provider.start(machine_request)
            return success(_describe_machine(machine))
            
    def running_machines(post):
        machines = provider.list_running_machines()
        return success(map(_describe_machine, machines))
        
    machines = view({
        "POST": start,
        "GET": running_machines,
    })
        
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
        return machine_description.describe_machine(machine)
    
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
