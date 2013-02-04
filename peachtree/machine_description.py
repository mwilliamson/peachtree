from . import dictobj


def describe_machine(machine):
    return {
        "identifier": machine.identifier,
        "name": machine.name,
        "imageName": machine.image_name,
        "externalHostname": machine.external_hostname(),
        "users": map(dictobj.obj_to_dict, machine.users()),
    }
