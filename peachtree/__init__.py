from . import qemu


provider = qemu.QemuProvider()


def start_kvm(image_name, public_ports=None):
    return provider.start(image_name, public_ports)


def find_running_machine(identifier):
    return provider.find_running_machine(identifier)


def list_running_machines():
    return provider.list_running_machines()
