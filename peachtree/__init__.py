from .qemu import qemu_provider
from .remote import remote_provider


__all__ = ["qemu_provider", "remote_provider", "providers"]


providers = {
    "qemu": qemu_provider,
}
