import collections

from . import dictobj


def describe_machine(machine):
    return collections.OrderedDict([
        ("identifier", machine.identifier),
        ("name", machine.name),
        ("imageName", machine.image_name),
        ("sshInternalPort", machine.ssh_internal_port),
        ("externalHostname", machine.external_hostname()),
        ("users", map(dictobj.obj_to_dict, machine.users())),
    ])
