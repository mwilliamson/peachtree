from . import qemu


provider = qemu.QemuProvider()


def start_kvm(machine_name, public_ports=None):
    return provider.start(machine_name, public_ports)


def find_running_vm(vm_id):
    return provider.find_running_vm(vm_id)


def list_running_machines():
    return provider.list_running_machines()
