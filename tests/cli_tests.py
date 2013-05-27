import contextlib
import os
import json
import itertools

import spur

import peachtree
from peachtree.request import request_machine, MachineRequest
from peachtree.machines import MachineWrapper
from peachtree.remote import RemoteMachine, RemoteProvider
from . import provider_tests
from .tempdir import create_temporary_dir


# TODO: remove duplication of copying images and image names between tests
_IMAGE_NAME="ubuntu-precise-amd64"
_WINDOWS_IMAGE_NAME="windows-server-2012-x86-64"


@contextlib.contextmanager
def create_cli_provider():
    with create_temporary_dir() as data_dir:
        def _pick_image(name):
            image_path = peachtree.qemu.Images().image_path(name)
            temp_image_path = peachtree.qemu.Images(data_dir).image_path(name)
            if not os.path.exists(os.path.dirname(temp_image_path)):
                os.makedirs(os.path.dirname(temp_image_path))
            os.symlink(image_path, temp_image_path)    
        
        _pick_image(_IMAGE_NAME)
        _pick_image(_WINDOWS_IMAGE_NAME)
        
        provider = RemoteProvider(CliApi(data_dir, spur.LocalShell()))
        try:
            yield provider
        finally:
            for machine in provider.list_running_machines():
                machine.destroy()


class CliApi(object):
    def __init__(self, data_dir, shell):
        self._data_dir = data_dir
        self._shell = shell
    
    def start(self, request):
        public_port_args = self._generate_public_port_args(request)
        run_result = self._run(
            ["run", request.image_name] + public_port_args
        )
        return json.loads(run_result.output)
    
    def start_many(self, requests):
        def generate_request_args(request):
            public_port_args = self._generate_public_port_args(request)
            return [
                "--request",
                "--name", request.name,
                "--image", request.image_name,
            ] + public_port_args
        
        requests_args = _flatten(map(generate_request_args, requests))
        run_result = self._run(["run-many"] + requests_args)
        return json.loads(run_result.output)
    
    def running_machine(self, identifier):
        describe_result = self._run(["describe", identifier])
        return json.loads(describe_result.output)
    
    def running_machines(self):
        result = self._run(["describe-all"])
        return json.loads(result.output)
    
    def is_running(self, identifier):
        return self.running_machine(identifier) is not None
    
    def destroy(self, identifier):
        self._run(["stop", identifier])
    
    def list_images(self):
        result = self._run(["list-images"])
        return json.loads(result.output)
    
    def _generate_public_port_args(self, request):
        return [
            "--public-port={0}".format(port)
            for port in request.public_ports
        ]
    
    def _run(self, command):
        data_dir_arg = "--qemu-data-dir={0}".format(self._data_dir)
        format_arg = "--output-format=json"
        return self._shell.run(["peachtree", data_dir_arg, format_arg] + command)


def _flatten(list_of_lists):
    return list(itertools.chain.from_iterable(list_of_lists))


CliTests = provider_tests.create(
    "CliTests",
    create_cli_provider
)
