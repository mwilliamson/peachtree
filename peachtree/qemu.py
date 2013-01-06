import os
import uuid
import time
import socket
import sys
import json
import errno
import collections
import threading

import paramiko
import spur
import starboard


local_shell = spur.LocalShell()


class QemuProvider(object):
    def __init__(self, data_dir=None, virtualiser=None):
        self._data_dir = data_dir or self._default_data_dir()
        self._virtualiser = virtualiser or Qemu()
    
    def start(self, image_name, public_ports=None, timeout=None):
        image_path = self.image_path(image_name)
        identifier = str(uuid.uuid4())
        public_ports = set([_GUEST_SSH_PORT] + (public_ports or []))
        forwarded_ports = self._generate_forwarded_ports(public_ports)
        
        self._write_status(identifier, image_name, forwarded_ports, timeout)
        
        return self._virtualiser.start(image_path, forwarded_ports, identifier)
        
    def _generate_forwarded_ports(self, public_ports):
        forwarded_ports = {}
        for port in public_ports:
            forwarded_ports[port] = self._allocate_host_port(port)
        return forwarded_ports
        
    def _allocate_host_port(self, guest_port):
        return starboard.find_local_free_tcp_port()
    
    def _write_status(self, identifier, image_name, forwarded_ports, timeout):
        start_time = time.time()
        status = {
            "imageName": image_name,
            "forwardedPorts": forwarded_ports,
            "startTime": start_time,
            "timeout": timeout
        }
        status_path = self._status_path(identifier)
        
        if not os.path.exists(os.path.dirname(status_path)):
            os.makedirs(os.path.dirname(status_path))
            
        with open(status_path, "w") as status_file:
            json.dump(status, status_file)
        
    def find_running_machine(self, identifier):
        machine = self._find_machine(identifier)
        if not machine.is_running():
            raise self._no_such_machine_error(identifier)
        return machine
        
    def _find_machine(self, identifier):
        status = self._read_status(identifier)
        if status is None:
            raise self._no_such_machine_error(identifier)
        return self._machine_from_status(status)
        
    def _machine_from_status(self, status):
        return self._virtualiser.machine_from_status(status)
    
    def _no_such_machine_error(self, identifier):
        message = 'Could not find running VM with id "{0}"'.format(identifier)
        return RuntimeError(message)
    
    def image_path(self, image_name):
        return os.path.join(self._data_dir, "images/{0}.qcow2".format(image_name))
    
    def _status_path(self, identifier):
        return os.path.join(self._status_dir(), identifier)
        
    def _status_dir(self):
        return os.path.join(self._data_dir, "status")
    
    def _default_data_dir(self):
        xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        return os.path.join(xdg_data_home, "peachtree/qemu")
    
    def list_running_machines(self):
        self._clean_status_dir()
        return self._read_statuses()
    
    def _clean_status_dir(self):
        if not os.path.exists(self._status_dir()):
            return
        identifiers = os.listdir(self._status_dir())
        for identifier in identifiers:
            machine = self._find_machine(identifier)
            if not machine.is_running():
                try:
                    os.remove(os.path.join(self._status_dir(), identifier))
                except IOError as error:
                    if error.errno != errno.ENOENT:
                        raise
                        
    def _read_statuses(self):
        if not os.path.exists(self._status_dir()):
            return []
        identifiers = os.listdir(self._status_dir())
        statuses = map(self._read_status, identifiers)
        return filter(lambda status: status is not None, statuses)
    
    def _read_status(self, identifier):
        status_file_path = os.path.join(self._status_dir(), identifier)
        try:
            with open(status_file_path) as status_file:
                status_json = json.load(status_file)
            return MachineStatus(identifier, status_json)
        except IOError as error:
            # ENOENT: Machine has been shut down in the interim, so ignore
            if error.errno == errno.ENOENT:
                return None
            else:
                raise
                
    def cron(self):
        self._stop_machines_past_timeout()
        self._clean_status_dir()
        
    def _stop_machines_past_timeout(self):
        statuses = self._read_statuses()
        for status in statuses:
            if status.timeout is not None:
                running_time = time.time() - status.start_time
                if running_time > status.timeout:
                    self._machine_from_status(status).destroy()


class Qemu(object):
    def start(self, image_path, forwarded_ports, identifier):
        kvm_forward_ports = [
            "hostfwd=tcp::{0}-:{1}".format(host_port, guest_port)
            for guest_port, host_port
            in forwarded_ports.iteritems()
        ]
        process = local_shell.spawn([
            "kvm", "-machine", "accel=kvm", "-snapshot",
            "-nographic", "-serial", "none",
            "-m", "512",
            "-drive", "file={0},if=virtio".format(image_path),
            "-netdev", "user,id=guest0," + ",".join(kvm_forward_ports),
            "-device", "virtio-net-pci,netdev=guest0",
            "-uuid", identifier,
        ])
        
        machine = QemuMachine(identifier, forwarded_ports)
        self._wait_for_ssh(process, machine)
        
        return machine
        
    def machine_from_status(self, status):
        return QemuMachine(status.identifier, forwarded_ports=status.forwarded_ports)
    
    def _wait_for_ssh(self, process, machine):
        for i in range(0, 60):
            try:
                if not process.is_running():
                    raise process.wait_for_result().to_error()
                machine.root_shell().run(["true"])
                return
            except (socket.error, paramiko.SSHException):
                last_exception = sys.exc_info()
                time.sleep(1)
        
        raise last_exception[0], last_exception[1], last_exception[2]


class MachineStatus(object):
    _fields = [
        ("imageName", "image_name"),
        ("forwardedPorts", "forwarded_ports"),
        ("startTime", "start_time"),
        ("timeout", "timeout"),
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
        
    def machine_from_status(self, status):
        return QemuMachine(status.identifier, forwarded_ports=status.forwarded_ports)


class QemuMachine(object):
    unprivileged_username = "qemu-user"
    hostname = "127.0.0.1"
    _password = "password1"
    
    def __init__(self, identifier, forwarded_ports):
        self.identifier = identifier
        self._forwarded_ports = forwarded_ports
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.destroy()
    
    def is_running(self):
        return self._process_id() is not None
    
    def destroy(self):
        process_id = self._process_id()
        if process_id is not None:
            local_shell.run(["kill", str(process_id)])
        
    def _process_id(self):
        pgrep_regex = "^kvm .*{0}".format(self.identifier)
        result = local_shell.run(["pgrep", "-f", pgrep_regex], allow_error=True)
        # Return code of 1 indicates no processes matched
        if result.return_code not in [0, 1]:
            raise result.to_error()
        process_ids = [int(line) for line in result.output.split("\n") if line]
        if len(process_ids) > 1:
            raise RuntimeError("Multiple processes found for VM")
        if process_ids:
            return process_ids[0]
        else:
            return None
    
    def restart(self):
        tmp_file = os.path.join("/tmp/", str(uuid.uuid4()))
        root_shell = self.root_shell()
        root_shell.run(["touch", tmp_file])
        root_shell.spawn(["reboot"])
        for i in range(0, 20):
            try:
                # TODO: automatic reconnection of shell
                result = self.root_shell().run(
                    ["test", "-f", tmp_file],
                    allow_error=True
                )
                if result.return_code == 1:
                    return
            except (socket.error, paramiko.SSHException, EOFError):
                pass
            time.sleep(1)
        raise RuntimeError("Failed to restart VM")
    
    def root_shell(self):
        return self.shell("root")
        
    def shell(self, user=None):
        config = self.ssh_config(user)
        return config.shell()
        
    def ssh_config(self, user=None):
        if user is None:
            user = self.unprivileged_username
        return SshConfig(
            hostname="127.0.0.1",
            port=self.public_port(_GUEST_SSH_PORT),
            username=user,
            password=self._password
        )
        
    def public_port(self, guest_port):
        return self._forwarded_ports[guest_port]


class SshConfig(object):
    def __init__(self, hostname, port, username, password):
        self.hostname = hostname
        self.port = port
        self.user = username
        self.password = password

    def shell(self):
        return spur.SshShell(
            hostname=self.hostname,
            port=self.port,
            username=self.user,
            password=self.password
        )
    

_GUEST_SSH_PORT = 22
