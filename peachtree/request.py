from . import dictobj


def request_machine(name, image_name, public_ports=None, timeout=None):
    if public_ports is None:
        public_ports = []
    return MachineRequest(name, image_name, public_ports, timeout)


MachineRequest = dictobj.data_class(
    "MachineRequest",
    ["name", "image_name", "public_ports", "timeout"]
)
