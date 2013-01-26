import os
import uuid
import time

import spur.ssh

from .sshconfig import SshConfig


class MachineWrapper(object):
    _delegates = [
        "identifier",
        "image_name",
        "hostname",
        "is_running",
        "public_port",
        "destroy",
        "users",
    ]
    
    def __init__(self, machine):
        self._machine = machine
        for delegate in self._delegates:
            setattr(self, delegate, getattr(self._machine, delegate))
    
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
            hostname=self.hostname(),
            port=self.public_port(_GUEST_SSH_PORT),
            user=user.username,
            password=user.password
        )
    
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
            except spur.ssh.ConnectionError:
                pass
            time.sleep(1)
        raise RuntimeError("Failed to restart VM")
        
    def _find_user(self, username):
        
        if username is None:
            condition = lambda user: not user.is_root
        else:
            condition = lambda user: user.username == username
            
        return filter(condition, self.users())[0]
        

# TODO: don't assume SSH port of 22
_GUEST_SSH_PORT = 22
