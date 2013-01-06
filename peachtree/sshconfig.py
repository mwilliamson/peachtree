import spur


_fields = [
    "hostname",
    "port",
    "user",
    "password",
]


def to_dict(ssh_config):
    return dict(
        (field, getattr(ssh_config, field))
        for field in _fields
        if hasattr(ssh_config, field)
    )
    
    
def from_dict(ssh_dict):
    kwargs = dict(
        (key, value)
        for key, value in ssh_dict.iteritems()
        if key in _fields
    )
    return SshConfig(**kwargs)


class SshConfig(object):
    def __init__(self, hostname, port, user, password):
        self.hostname = hostname
        self.port = port
        self.user = user
        self.password = password

    def shell(self):
        return spur.SshShell(
            hostname=self.hostname,
            port=self.port,
            username=self.user,
            password=self.password
        )
