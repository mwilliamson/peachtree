from . import qemu


provider = qemu.Provider()


def start_kvm(image_name, public_ports=None, timeout=None):
    return provider.start(image_name, public_ports, timeout)


def find_running_machine(identifier):
    return provider.find_running_machine(identifier)


def list_running_machines():
    return provider.list_running_machines()


def cron():
    return provider.cron()
