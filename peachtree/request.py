import collections


def request_machine(name, image_name, public_ports=None, timeout=None):
    if public_ports is None:
        public_ports = []
    return MachineRequest(name, image_name, public_ports, timeout)


MachineRequest = collections.namedtuple(
    "MachineRequest",
    ["name", "image_name", "public_ports", "timeout"]
)
