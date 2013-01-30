import os
import uuid
import time
import json
import errno
import itertools

import spur
import spur.ssh
import starboard

from . import wait
from .users import User
from .machines import MachineWrapper
from . import processes
from . import dictobj

local_shell = spur.LocalShell()


def qemu_provider(command=None, accel_arg=None, networking=None, data_dir=None):
    if accel_arg is None:
        accel_arg = "kvm:tcg"
    
    if command is None:
        command = _find_qemu_command()
    
    if networking is None:
        networking = UserNetworking()
        
    data_dir = data_dir or _default_data_dir()
    images = Images(data_dir)
    invoker = QemuInvoker(command, accel_arg, images)
    statuses = Statuses(os.path.join(data_dir, "status"))
    return Provider(invoker, networking, statuses)


def _find_qemu_command():
    for command in ["qemu", "kvm"]:
        if local_shell.run(["which", command], allow_error=True).return_code == 0:
            return command
    raise RuntimeError("Could not find qemu")


class Provider(object):
    def __init__(self, invoker, networking, statuses):
        self._invoker = invoker
        self._networking = networking
        self._statuses = statuses
    
    def start(self, image_name, public_ports=None, timeout=None):
        identifier = str(uuid.uuid4())
        public_ports = set([_GUEST_SSH_PORT] + (public_ports or []))
        forwarded_ports = self._generate_forwarded_ports(public_ports)
        
        process_set = processes.start({})
        # TODO: kill processes started by network if exception is raised
        network = self._networking.start(forwarded_ports, process_set)
        self._invoker.start_process(image_name, network, process_set)
        
        status = MachineStatus(
            identifier=identifier,
            image_name=image_name,
            forwarded_ports=forwarded_ports,
            timeout=timeout,
            start_time=time.time(),
            process_set_run_dir=process_set.run_dir
        )
        
        self._statuses.write(status)
        machine = _create_machine(status, self._statuses)
        
        try:
            self._wait_for_ssh(process_set, machine)
            return machine
        except:
            machine.destroy()
            raise
            
    def start_many(self, requests):
        return MachineSet(map(self._start_request, requests))
    
    def _start_request(self, request):
        return self.start(request.image_name)
    
    def _generate_forwarded_ports(self, public_ports):
        return dict(
            (port, self._allocate_host_port(port))
            for port in public_ports
        )
        
    def _allocate_host_port(self, guest_port):
        return starboard.find_local_free_tcp_port()
        
    def _wait_for_ssh(self, process_set, machine):
        def attempt_ssh_command():
            if not process_set.all_running():
                process_set.kill_all()
                wait.wait_until_not(process_set.any_running, timeout=1, wait_time=0.1)
                output = process_set.all_output()
                raise RuntimeError("Process died, output:\n{0}".format(output))
            machine.root_shell().run(["true"])
            
        wait.wait_until_successful(
            attempt_ssh_command,
            errors=(spur.ssh.ConnectionError, ),
            timeout=60,
            wait_time=1
        )
        
    def find_running_machine(self, identifier):
        machine = self._find_machine(identifier)
        if machine is None:
            return None
        elif machine.is_running():
            return machine
        else:
            return None
        
    def _find_machine(self, identifier):
        status = self._statuses.read(identifier)
        if status is None:
            return None
        else:
            return self._machine_from_status(status)
        
    def _machine_from_status(self, status):
        return _create_machine(status, self._statuses)
    
    def list_running_machines(self):
        statuses = self._statuses.read_all()
        machines = map(self._machine_from_status, statuses)
        return [machine for machine in machines if machine is not None]
                
    def cron(self):
        self._stop_machines_past_timeout()
        self._clean_statuses()
        
    def _stop_machines_past_timeout(self):
        statuses = self._statuses.read_all()
        for status in statuses:
            if status.timeout is not None:
                running_time = time.time() - status.start_time
                if running_time > status.timeout:
                    self._machine_from_status(status).destroy()
    
    def _clean_statuses(self):
        for status in self._statuses.read_all():
            machine = self._machine_from_status(status)
            if not machine.is_running():
                self._statuses.remove(status.identifier)


class QemuInvoker(object):
    def __init__(self, command, accel_arg, images):
        self._command = command
        self._accel_arg = accel_arg
        self._images = images
        
    def start_process(self, image_name, network, process_set):
        image_path = self._images.image_path(image_name)
        netdev_arg = network.qemu_netdev_arg()
        qemu_command = [
            self._command, "-machine", "accel={0}".format(self._accel_arg),
            "-snapshot",
            "-nographic", "-serial", "none",
            "-m", "512",
            "-drive", "file={0},if=virtio".format(image_path),
            "-netdev", "{0},id=guest0".format(netdev_arg),
            "-device", "virtio-net-pci,netdev=guest0",
        ]
        process_set.start({"qemu": qemu_command})


class Images(object):
    def __init__(self, data_dir=None):
        self._data_dir = data_dir or _default_data_dir()
        
    def image_path(self, image_name):
        return os.path.join(self._data_dir, "images/{0}.qcow2".format(image_name))

    
def _default_data_dir():
    xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(xdg_data_home, "peachtree/qemu")
    

MachineStatus = dictobj.data_class("MachineStatus",
    [
        "identifier",
        "image_name",
        "forwarded_ports",
        "start_time",
        "timeout",
        "process_set_run_dir",
    ]
)


class MachineSet(object):
    def __init__(self, machines):
        self._machines = machines
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        for machine in self._machines:
            machine.destroy()
            
    def __getitem__(self, index):
        return self._machines[index]


class Statuses(object):
    def __init__(self, status_dir):
        self._status_dir = status_dir
        
    def remove(self, identifier):
        try:
            os.remove(self._status_path(identifier))
        except OSError as error:
            # ENOENT: Machine has been shut down in the interim, so ignore
            if error.errno != errno.ENOENT:
                raise
    
    def write(self, status):
        status_json = dictobj.obj_to_dict(status)
        self._write_json(status.identifier, status_json)
    
    def read(self, identifier):
        try:
            status_dict = self._read_json(identifier)
        except IOError as error:
            # ENOENT: Machine has been shut down in the interim, so ignore
            if error.errno == errno.ENOENT:
                return None
            else:
                raise
        
        status_dict["forwardedPorts"] = dict(
            (int(guest_port), host_port)
            for guest_port, host_port
            in status_dict["forwardedPorts"].iteritems()
        )
        status = dictobj.dict_to_obj(status_dict, MachineStatus)
        return status
                        
    def read_all(self):
        if not os.path.exists(self._status_dir):
            return []
        identifiers = os.listdir(self._status_dir)
        statuses = map(self.read, identifiers)
        return filter(lambda status: status is not None, statuses)
    
    def _status_path(self, identifier):
        return os.path.join(self._status_dir, identifier)

    def _read_json(self, identifier):
        status_file_path = self._status_path(identifier)
        with open(status_file_path) as status_file:
            return json.load(status_file)
    
    def _write_json(self, identifier, data):
        status_path = self._status_path(identifier)
        
        if not os.path.exists(os.path.dirname(status_path)):
            os.makedirs(os.path.dirname(status_path))
            
        with open(status_path, "w") as status_file:
            json.dump(data, status_file)


def _create_machine(*args, **kwargs):
    machine = QemuMachine(*args, **kwargs)
    return MachineWrapper(machine)


class QemuMachine(object):
    _password = "password1"
    _users = [
        User("qemu-user", _password, is_root=False),
        User("root", _password, is_root=True),
    ]
    
    def __init__(self, status, statuses):
        self.image_name = status.image_name
        self.identifier = status.identifier
        self._process_set = processes.from_dir(status.process_set_run_dir)
        self._forwarded_ports = status.forwarded_ports
        self._statuses = statuses
    
    def is_running(self):
        return self._process_set.all_running()
    
    def destroy(self):
        self._process_set.kill_all()
        
        wait.wait_until_not(
            self._process_set.any_running, timeout=10, wait_time=0.1,
            error_message="Failed to kill VM {0}".format(self.identifier)
        )
        
        self._statuses.remove(self.identifier)
        
    def public_port(self, guest_port):
        return self._forwarded_ports.get(guest_port, None)
        
    def hostname(self):
        return starboard.find_local_hostname()
        
    def users(self):
        return self._users


_GUEST_SSH_PORT = 22


class UserNetworking(object):
    def start(self, forwarded_ports, process_set):
        return UserNetwork(forwarded_ports)


class UserNetwork(object):
    def __init__(self, forwarded_ports):
        self._forwarded_ports = forwarded_ports
        
    def qemu_netdev_arg(self):
        kvm_forward_ports = [
            "hostfwd=tcp::{0}-:{1}".format(host_port, guest_port)
            for guest_port, host_port
            in self._forwarded_ports.iteritems()
        ]
        return "user," + ",".join(kvm_forward_ports)
