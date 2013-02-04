import contextlib
import os
import json

import spur

import peachtree
from peachtree.request import request_machine, MachineRequest
from peachtree.machines import MachineWrapper
from peachtree.remote import RemoteMachine
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
        
        provider = CliProvider(data_dir, spur.LocalShell())
        try:
            yield provider
        finally:
            for machine in provider.list_running_machines():
                machine.destroy()


class CliProvider(object):
    def __init__(self, data_dir, shell):
        self._cli_api = CliApi(data_dir, shell)
    
    def start(self, *args, **kwargs):
        # TODO: remove duplication with QemuProvider.start
        if len(args) == 1 and not kwargs and isinstance(args[0], MachineRequest):
            request = args[0]
        else:
            request = request_machine(*(["peachtree"] + list(args)), **kwargs)
            
        machine_desc = self._cli_api.start(request)
        return MachineWrapper(RemoteMachine(machine_desc, self._cli_api))
    
    def list_running_machines(self):
        return []


class CliApi(object):
    def __init__(self, data_dir, shell):
        self._data_dir = data_dir
        self._shell = shell
    
    def start(self, request):
        run_result = self._run([
            "run", request.image_name,
        ])
        return json.loads(run_result.output)
    
    def destroy(self, identifier):
        pass
        
    def public_port(self, identifier, port):
        run_result = self._run(["public-port", identifier, str(port)])
        return int(run_result.output.strip())
    
    def _run(self, command):
        data_dir_arg = "--qemu-data-dir={0}".format(self._data_dir)
        return self._shell.run(["peachtree", data_dir_arg] + command)


CliTests = provider_tests.create(
    "CliTests",
    create_cli_provider
)
