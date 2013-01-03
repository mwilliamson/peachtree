from . import qemu

def start_kvm(machine_name):
    provider = qemu.QemuProvider()
    vm = provider.create(machine_name, [])
    vm.start()
    return vm
