from . import qemu


def qemu_provider(*args, **kwargs):
    return qemu.Provider(["qemu"], *args, **kwargs)

    
def kvm_provider(*args, **kwargs):
    return qemu.Provider(["kvm", "-machine", "accel=kvm"], *args, **kwargs)


providers = {
    "qemu": qemu_provider,
    "kvm": kvm_provider,
}
