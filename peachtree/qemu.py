import os
import uuid
import time
import json
import errno

import psutil
import spur
import spur.ssh
import starboard

from . import wait
from .users import User
from .machines import MachineWrapper

local_shell = spur.LocalShell()


def qemu_provider(command=None, accel_arg=None, *args, **kwargs):
    if accel_arg is None:
        accel_arg = "kvm:tcg"
    
    if command is None:
        command = _find_qemu_command()
    
    networking = UserNetworking()
    
    return Provider(command, accel_arg, networking, *args, **kwargs)


def _find_qemu_command():
    for command in ["qemu", "kvm"]:
        if local_shell.run(["which", command], allow_error=True).return_code == 0:
            return command
    raise RuntimeError("Could not find qemu")


class Provider(object):
    def __init__(self, command, accel_arg, networking, data_dir=None):
        self._command = command
        self._accel_arg = accel_arg
        self._networking = networking
        self._data_dir = data_dir or _default_data_dir()
        self._statuses = Statuses(self._status_dir())
        self._images = Images(self._data_dir)
    
    def start(self, image_name, public_ports=None, timeout=None):
        image_path = self._images.image_path(image_name)
        identifier = str(uuid.uuid4())
        public_ports = set([_GUEST_SSH_PORT] + (public_ports or []))
        forwarded_ports = self._generate_forwarded_ports(public_ports)
        
        self._statuses.write(identifier, image_name, forwarded_ports, timeout)
        process = self._start_process(image_path, forwarded_ports)
        process_start_time = _process_start_time_from_pid(process.pid)
        self._statuses.update(identifier, process.pid, process_start_time)
        
        status = self._statuses.read(identifier)
        machine = _create_machine(status, self._statuses)
        
        try:
            self._wait_for_ssh(process, machine)
            return machine
        except:
            machine.destroy()
            raise
        
    def _generate_forwarded_ports(self, public_ports):
        return dict(
            (port, self._allocate_host_port(port))
            for port in public_ports
        )
        
    def _allocate_host_port(self, guest_port):
        return starboard.find_local_free_tcp_port()
        
    def _start_process(self, image_path, forwarded_ports):
        return local_shell.spawn([
            self._command, "-machine", "accel={0}".format(self._accel_arg),
            "-snapshot",
            "-nographic", "-serial", "none",
            "-m", "512",
            "-drive", "file={0},if=virtio".format(image_path),
        ] + self._networking.qemu_args(forwarded_ports), store_pid=True)
        
    def _wait_for_ssh(self, process, machine):
        def attempt_ssh_command():
            if not process.is_running():
                raise process.wait_for_result().to_error()
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
    
    def _status_dir(self):
        return os.path.join(self._data_dir, "status")


class Images(object):
    def __init__(self, data_dir=None):
        self._data_dir = data_dir or _default_data_dir()
        
    def image_path(self, image_name):
        return os.path.join(self._data_dir, "images/{0}.qcow2".format(image_name))

    
def _default_data_dir():
    xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(xdg_data_home, "peachtree/qemu")
    

class MachineStatus(object):
    _fields = [
        ("imageName", "image_name"),
        ("forwardedPorts", "forwarded_ports"),
        ("startTime", "start_time"),
        ("timeout", "timeout"),
        ("pid", "pid"),
        ("processStartTime", "process_start_time"),
    ]
    
    def __init__(self, identifier, json):
        self.identifier = identifier
        for json_name, py_name in self._fields:
            setattr(self, py_name, json[json_name])
        
        self.forwarded_ports = dict(
            (int(guest_port), host_port)
            for guest_port, host_port
            in self.forwarded_ports.iteritems()
        )


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
    
    def write(self, identifier, image_name, forwarded_ports, timeout):
        start_time = time.time()
        status = {
            "imageName": image_name,
            "forwardedPorts": forwarded_ports,
            "startTime": start_time,
            "timeout": timeout,
        }
        self._write_json(identifier, status)
    
    def update(self, identifier, pid, process_start_time):
        status_json = self._read_json(identifier)
        status_json["pid"] = pid
        status_json["processStartTime"] = process_start_time
        self._write_json(identifier, status_json)
    
    def read(self, identifier):
        try:
            status_json = self._read_json(identifier)
            return MachineStatus(identifier, status_json)
        except IOError as error:
            # ENOENT: Machine has been shut down in the interim, so ignore
            if error.errno == errno.ENOENT:
                return None
            else:
                raise
                        
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
    unprivileged_user = User("qemu-user", _password)
    root_user = User("root", _password)
    users = [unprivileged_user, root_user]
    
    def __init__(self, status, statuses):
        self.image_name = status.image_name
        self.identifier = status.identifier
        self._pid = status.pid
        self._process_start_time = status.process_start_time
        self._forwarded_ports = status.forwarded_ports
        self._statuses = statuses
    
    def is_running(self):
        if not _process_is_running(self._pid):
            return False
        return _process_start_time_from_pid(self._pid) == self._process_start_time
    
    def destroy(self):
        if self.is_running():
            local_shell.run(["kill", str(self._pid)])
        
        wait.wait_until_not(
            self.is_running, timeout=10, wait_time=0.1,
            error_message="Failed to kill VM {0}".format(self.identifier)
        )
        
        self._statuses.remove(self.identifier)
        
    def public_port(self, guest_port):
        return self._forwarded_ports.get(guest_port, None)
        
    def hostname(self):
        return starboard.find_local_hostname()


def _process_start_time_from_pid(pid):
    return int(psutil.Process(pid).create_time)


def _process_is_running(pid):
    status = psutil.Process(pid).status
    return status not in [psutil.STATUS_DEAD, psutil.STATUS_ZOMBIE]


_GUEST_SSH_PORT = 22

class UserNetworking(object):
    def qemu_args(self, forwarded_ports):
        kvm_forward_ports = [
            "hostfwd=tcp::{0}-:{1}".format(host_port, guest_port)
            for guest_port, host_port
            in forwarded_ports.iteritems()
        ]
        return [
            "-netdev", "user,id=guest0," + ",".join(kvm_forward_ports),
            "-device", "virtio-net-pci,netdev=guest0",
        ]
