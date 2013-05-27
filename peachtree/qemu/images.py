import os
import json

from .. import dictobj
from .common import default_data_dir as _default_data_dir
from ..users import User


class Images(object):
    def __init__(self, data_dir=None):
        data_dir = data_dir or _default_data_dir()
        self._images_dir = os.path.join(data_dir, "images")
    
    def all(self):
        return sorted(
            map(self.image, os.listdir(self._images_dir)),
            key=lambda image: image.name
        )
    
    def image_path(self, image_name):
        return os.path.join(self._images_dir, image_name)
    
    def image(self, image_name):
        image_dir = self.image_path(image_name)
        with open(os.path.join(image_dir, "image.json")) as description_file:
            description = json.load(description_file)
        relative_disks = description["disks"]
        disks = [
            os.path.abspath(os.path.join(image_dir, relative_disk))
            for relative_disk in relative_disks
        ]
        memory_size = description.get("memory", 512)
        
        users_json = description.get("users", None)
        if users_json is None:
            password = "password1"
            users = [
                User("qemu-user", password, is_root=False),
                User("root", password, is_root=True),
            ]
        else:
            users = [
                dictobj.dict_to_obj(user_json, User)
                for user_json in users_json
            ]
            
        operating_system_family = description.get("operatingSystemFamily", "linux")
        ssh_internal_port = description.get("sshPort", 22)
            
        return Image(
            name=image_name,
            disks=disks,
            memory_size=memory_size,
            users=users,
            operating_system_family=operating_system_family,
            ssh_internal_port=ssh_internal_port,
        )


Image = dictobj.data_class("Image", [
    "name",
    "disks",
    "memory_size",
    "users",
    "operating_system_family",
    "ssh_internal_port",
])
