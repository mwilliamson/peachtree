from .qemu import qemu_provider
from .remote import remote_provider
from .request import request_machine

__all__ = ["qemu_provider", "remote_provider", "providers", "request_machine"]


providers = {
    "qemu": qemu_provider,
}
