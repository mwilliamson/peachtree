import collections


def request_machine(image_name, timeout=None):
    return MachineRequest(image_name, timeout)


MachineRequest = collections.namedtuple("MachineRequest", ["image_name", "timeout"])
