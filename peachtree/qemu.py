import os
import uuid
import time
import socket
import sys

import paramiko
import spur
import starboard


local_shell = spur.LocalShell()


class QemuProvider(object):
    def create(self, machine_name, public_ports):
        image_path = self._image_path(machine_name)
        vm_id = str(uuid.uuid4())
        
        return QemuMachine(vm_id, image_path, [_GUEST_SSH_PORT] + public_ports)
        
    def find_running_vm(self, vm_id):
        return QemuMachine(
            vm_id,
            image_path=None,
            public_ports=None
        )
    
    def _image_path(self, machine_name):
        return os.path.join(self._data_dir(), "images/{0}.qcow2".format(machine_name))
        
    def _data_dir(self):
        xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        return os.path.join(xdg_data_home, "peachtree/qemu")
        


class QemuMachine(object):
    unprivileged_username = "qemu-user"
    hostname = "127.0.0.1"
    _password = "password1"
    
    def __init__(self, vm_id, image_path, public_ports):
        self._image_path = image_path
        self._public_ports = public_ports
        self.vm_id = vm_id
    
    def __enter__(self):
        if not self.is_running():
            self.start()
        return self
        
    def __exit__(self, *args):
        self.destroy()
    
    def start(self):
        if self.is_running():
            raise RuntimeError("VM is already running")
        
        self._generate_forwarded_ports()
        
        kvm_forward_ports = []
        for guest_port, host_port in self._forwarded_ports.iteritems():
            kvm_forward_ports.append("hostfwd=tcp::{0}-:{1}".format(host_port, guest_port))
        process = local_shell.spawn([
            "kvm", "-machine", "accel=kvm", "-snapshot",
            "-nographic", "-serial", "none",
            "-m", "512",
            "-drive", "file={0},if=virtio".format(self._image_path),
            "-netdev", "user,id=guest0," + ",".join(kvm_forward_ports),
            "-device", "virtio-net-pci,netdev=guest0",
            "-uuid", self.vm_id,
        ])
        
        for i in range(0, 60):
            try:
                if not process.is_running():
                    raise process.wait_for_result().to_error()
                self.root_shell().run(["true"])
                return
            except (socket.error, paramiko.SSHException) as e:
                last_exception = sys.exc_info()
                time.sleep(1)
        
        raise last_exception[0], last_exception[1], last_exception[2]
    
    def is_running(self):
        return self._process_id() is not None
    
    def destroy(self):
        process_id = self._process_id()
        if process_id is not None:
            local_shell.run(["kill", str(process_id)])
        
    def _process_id(self):
        result = local_shell.run(["pgrep", "-f", self.vm_id], allow_error=True)
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
        
    def _generate_forwarded_ports(self):
        self._forwarded_ports = {}
        for port in self._public_ports:
            self._forwarded_ports[port] = self._allocate_host_port(port)
        
    def _allocate_host_port(self, guest_port):
        return starboard.find_local_free_tcp_port()


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
