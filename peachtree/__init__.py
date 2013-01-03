from . import qemu

def start_kvm(machine_name):
    provider = qemu.QemuProvider()
    return provider.create(machine_name, [])
