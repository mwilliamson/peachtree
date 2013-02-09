import os
import uuid

import spur.ssh

from .sshconfig import SshConfig
from . import wait


class MachineWrapper(object):
    _delegates = [
        "identifier",
        "name",
        "image_name",
        "ssh_internal_port",
        "external_hostname",
        "is_running",
        "forwarded_tcp_ports",
        "destroy",
        "users",
    ]
    
    def __init__(self, machine):
        self._machine = machine
        for delegate in self._delegates:
            setattr(self, delegate, getattr(self._machine, delegate))
        
    def public_port(self, guest_port):
        return self.forwarded_tcp_ports().get(guest_port, None)
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.destroy()
    
    def root_shell(self):
        root_username = next(
            user.username
            for user in self.users()
            if user.is_root
        )
        return self.shell(root_username)
        
    def shell(self, *args, **kwargs):
        config = self.ssh_config(*args, **kwargs)
        return config.shell()
        
    def ssh_config(self, username=None):
        user = self._find_user(username)
        return SshConfig(
            hostname=self.external_hostname(),
            port=self.public_port(self.ssh_internal_port),
            user=user.username,
            password=user.password
        )
    
    def restart(self):
        tmp_file = os.path.join("/tmp/", str(uuid.uuid4()))
        with self.root_shell() as root_shell:
            root_shell.run(["touch", tmp_file])
            root_shell.spawn(["reboot"])
            
        def has_restarted():
            try:
                # TODO: automatic reconnection of shell
                with self.root_shell() as root_shell:
                    result = root_shell.run(
                        ["test", "-f", tmp_file],
                        allow_error=True
                    )
                return result.return_code == 1
            except spur.ssh.ConnectionError:
                return False
            
        wait.wait_until(
            has_restarted, timeout=30, wait_time=1,
            error_message="Failed to restart VM"
        )
            
    def _find_user(self, username):
        
        if username is None:
            condition = lambda user: not user.is_root
        else:
            condition = lambda user: user.username == username
            
        return filter(condition, self.users())[0]
        

class MachineSet(object):
    def __init__(self, machines):
        self._machines = machines
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        for machine in self._machines:
            machine.destroy()
            
    def __getitem__(self, key):
        if isinstance(key, basestring):
            return next(
                machine
                for machine in self._machines
                if machine.name == key
            )
        elif isinstance(key, (int, long)):
            return self._machines[key]
        else:
            raise TypeError("Expected key to be string or integer")
