from . import qemu


def start_kvm(machine_name, public_ports=None):
    provider = qemu.QemuProvider()
    vm = provider.create(machine_name, public_ports or [])
    vm.start()
    return vm
