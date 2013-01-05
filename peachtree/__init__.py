from . import qemu


def start_kvm(machine_name, public_ports=None):
    provider = qemu.QemuProvider()
    return provider.start(machine_name, public_ports or [])


def find_running_vm(vm_id):
    provider = qemu.QemuProvider()
    return provider.find_running_vm(vm_id)
