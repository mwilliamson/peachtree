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
        image_path = os.path.expanduser("~/.local/share/qemu-provider/{0}.qcow2".format(machine_name))
        return QemuMachine(image_path, [_GUEST_SSH_PORT] + public_ports)


class QemuMachine(object):
    unprivileged_username = "qemu-user"
    hostname = "127.0.0.1"
    _password = "password1"
    
    def __init__(self, image_path, public_ports):
        self._image_path = image_path
        self._uuid = str(uuid.uuid4())
        self._running = False
        self._public_ports = public_ports
    
    def __enter__(self):
        if not self._running:
            self.start()
        return self
        
    def __exit__(self, *args):
        self.destroy()
    
    def start(self):
        if self._running:
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
            "-uuid", self._uuid
        ])
        self._running = True
        
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
    
    def destroy(self):
        kill_command = ["pkill", "-f", self._uuid]
        result = local_shell.run(kill_command, allow_error=True)
        # Return code of 1 indicates no processes killed
        if result.return_code not in [0, 1]:
            raise result.to_error()
        self._running = False
    
    def restart(self):
        tmp_file = os.path.join("/tmp/", str(uuid.uuid4()))
        root_shell = self.root_shell()
        root_shell.run(["touch", tmp_file])
        root_shell.spawn(["reboot"])
        for i in range(0, 20):
            has_rebooted_command = [
                "bash", "-c",
                "[ -f {0} ] && echo 1 || echo 0".format(tmp_file)
            ]
            try:
                # TODO: automatic reconnection of shell
                result = self.root_shell().run(has_rebooted_command)
                if result.output.strip() == "0":
                    return
            except (socket.error, paramiko.SSHException):
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
