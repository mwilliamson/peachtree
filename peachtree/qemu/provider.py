import os
import uuid
import time
import json
import errno
import random

import spur
import spur.ssh
import starboard

from .. import wait
from ..users import User
from ..machines import MachineWrapper
from .. import processes
from .. import dictobj
from ..request import request_machine, MachineRequest
from . import networkconfig
from .. import futures

local_shell = spur.LocalShell()


def qemu_provider(command=None, accel_arg=None, networking=None, data_dir=None):
    if accel_arg is None:
        accel_arg = "kvm:tcg"
    
    if command is None:
        command = _find_qemu_command()
    
    if networking is None:
        networking = UserNetworking()
        
    data_dir = data_dir or _default_data_dir()
    images = Images(data_dir)
    invoker = QemuInvoker(command, accel_arg)
    statuses = Statuses(os.path.join(data_dir, "status"))
    return Provider(invoker, images, networking, statuses)


def _find_qemu_command():
    for command in ["qemu", "kvm"]:
        if local_shell.run(["which", command], allow_error=True).return_code == 0:
            return command
    raise RuntimeError("Could not find qemu")


class Provider(object):
    def __init__(self, invoker, images, networking, statuses):
        self._invoker = invoker
        self._images = images
        self._networking = networking
        self._statuses = statuses
    
    def start(self, *args, **kwargs):
        if len(args) == 1 and not kwargs and isinstance(args[0], MachineRequest):
            request = args[0]
        else:
            request = request_machine(*(["peachtree"] + list(args)), **kwargs)
        image = self._images.image(request.image_name)
        network = self._networking.settings_for(image, request)
        machine = self._start_with_network_settings(request, network)
        
        config = self._guest_network_config_for(machine)
        machine.root_shell().run(self._append_host_command(
            "127.0.0.1", machine.name, config
        ))
        
        return machine
            
    def start_many(self, requests):
        # TODO: assert name of each request is unique
        network = self._networking.start_network()
        
        def start(request):
            image = self._images.image(request.image_name)
            network_settings = network.settings_for(image, request)
            return self._start_with_network_settings(request, network_settings)
        
        machines = list(futures.thread_map(start, requests))
        
        addresses = []
        for index, machine in enumerate(machines):
            request = requests[index]
            
            eth1_address = "192.168.0.{0}".format(1 + index)
            netmask = "255.255.255.0"
            with machine.root_shell() as root_shell:
                config = self._guest_network_config_for(machine)
                config.configure_internal_interface(
                    root_shell, eth1_address, netmask
                )
                addresses.append((request.name, eth1_address))
        
        for machine in machines:
            config = self._guest_network_config_for(machine)
            with machine.root_shell() as root_shell:
                for hostname, address in addresses:
                    root_shell.run(self._append_host_command(
                        address, hostname, config
                    ))
        
        return MachineSet(machines)
    
    def _guest_network_config_for(self, machine):
        image = self._images.image(machine.image_name)
        os_family = image.operating_system_family
        return networkconfig.network_config(os_family)
    
    def _append_host_command(self, address, hostname, network_config):
         # TODO: properly escape hosts_path
        sh_command = "echo {0} {1} >> '{2}'".format(
            address, hostname, network_config.hosts_path
        )
        return ["sh", "-c", sh_command]

    def _start_with_network_settings(self, request, network):
        image = self._images.image(request.image_name)
        identifier = str(uuid.uuid4())
        
        process_set = processes.start({})
        self._invoker.start_process(image, network, process_set)
        
        status = MachineStatus(
            name=request.name,
            identifier=identifier,
            image_name=request.image_name,
            ssh_internal_port=image.ssh_internal_port,
            # TODO: either re-couple network, or find a better way of
            # storing network details
            forwarded_ports=network.forwarded_ports,
            timeout=request.timeout,
            start_time=time.time(),
            process_set_run_dir=process_set.run_dir
        )
        
        self._statuses.write(status)
        machine = _create_machine(image.users, status, self._statuses)
        
        try:
            self._wait_for_ssh(process_set, machine)
            return machine
        except:
            machine.destroy()
            raise
        
    def _wait_for_ssh(self, process_set, machine):
        def attempt_ssh_command():
            if not process_set.all_running():
                process_set.kill_all()
                wait.wait_until_not(process_set.any_running, timeout=1, wait_time=0.1)
                output = process_set.all_output()
                raise RuntimeError("Process died, output:\n{0}".format(output))
            with machine.root_shell() as shell:
                shell.run(["true"])
            
        wait.wait_until_successful(
            attempt_ssh_command,
            errors=(spur.ssh.ConnectionError, ),
            timeout=180,
            wait_time=1
        )
        
    def find_running_machine(self, identifier):
        machine = self._find_machine(identifier)
        if machine is None:
            return None
        elif machine.is_running():
            return machine
        else:
            return None
        
    def _find_machine(self, identifier):
        status = self._statuses.read(identifier)
        if status is None:
            return None
        else:
            return self._machine_from_status(status)
        
    def _machine_from_status(self, status):
        image = self._images.image(status.image_name)
        return _create_machine(image.users, status, self._statuses)
    
    def list_running_machines(self):
        statuses = self._statuses.read_all()
        machines = map(self._machine_from_status, statuses)
        return [machine for machine in machines if machine is not None]
                
    def cron(self):
        self._stop_machines_past_timeout()
        self._clean_statuses()
        
    def _stop_machines_past_timeout(self):
        statuses = self._statuses.read_all()
        for status in statuses:
            if status.timeout is not None:
                running_time = time.time() - status.start_time
                if running_time > status.timeout:
                    self._machine_from_status(status).destroy()
    
    def _clean_statuses(self):
        for status in self._statuses.read_all():
            machine = self._machine_from_status(status)
            if not machine.is_running():
                self._statuses.remove(status.identifier)


class QemuInvoker(object):
    def __init__(self, command, accel_arg):
        self._command = command
        self._accel_arg = accel_arg
        
    def start_process(self, image, network, process_set):
        disk_args = []
        for disk in image.disks:
            disk_args += ["-drive", "file={0},if=virtio".format(disk)]
        
        qemu_command = [
            self._command, "-machine", "accel={0}".format(self._accel_arg),
            "-snapshot",
            "-nographic", "-serial", "none",
            "-m", str(image.memory_size),
        ] + disk_args + network.qemu_args()
        process_set.start({"qemu": qemu_command})


class Images(object):
    def __init__(self, data_dir=None):
        self._data_dir = data_dir or _default_data_dir()
    
    def image_path(self, image_name):
        return os.path.join(self._data_dir, "images", image_name)
    
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
            disks=disks,
            memory_size=memory_size,
            users=users,
            operating_system_family=operating_system_family,
            ssh_internal_port=ssh_internal_port,
        )


Image = dictobj.data_class("Image", [
    "disks",
    "memory_size",
    "users",
    "operating_system_family",
    "ssh_internal_port",
])

    
def _default_data_dir():
    xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(xdg_data_home, "peachtree-0.3/qemu")
    

MachineStatus = dictobj.data_class("MachineStatus",
    [
        "identifier",
        "name",
        "image_name",
        "ssh_internal_port",
        "forwarded_ports",
        "start_time",
        "timeout",
        "process_set_run_dir",
    ]
)


class MachineSet(object):
    def __init__(self, machines):
        self._machines = machines
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        for machine in self._machines:
            machine.destroy()
            
    def __getitem__(self, key):
        if isinstance(key, basestring):
            return next(
                machine
                for machine in self._machines
                if machine.name == key
            )
        elif isinstance(key, (int, long)):
            return self._machines[key]
        else:
            raise TypeError("Expected key to be string or integer")


class Statuses(object):
    def __init__(self, status_dir):
        self._status_dir = status_dir
        
    def remove(self, identifier):
        try:
            os.remove(self._status_path(identifier))
        except OSError as error:
            # ENOENT: Machine has been shut down in the interim, so ignore
            if error.errno != errno.ENOENT:
                raise
    
    def write(self, status):
        status_json = dictobj.obj_to_dict(status)
        self._write_json(status.identifier, status_json)
    
    def read(self, identifier):
        try:
            status_dict = self._read_json(identifier)
        except IOError as error:
            # ENOENT: Machine has been shut down in the interim, so ignore
            if error.errno == errno.ENOENT:
                return None
            else:
                raise
        
        status_dict["forwardedPorts"] = dict(
            (int(guest_port), host_port)
            for guest_port, host_port
            in status_dict["forwardedPorts"].iteritems()
        )
        status = dictobj.dict_to_obj(status_dict, MachineStatus)
        return status
                        
    def read_all(self):
        if not os.path.exists(self._status_dir):
            return []
        identifiers = os.listdir(self._status_dir)
        statuses = map(self.read, identifiers)
        return filter(lambda status: status is not None, statuses)
    
    def _status_path(self, identifier):
        return os.path.join(self._status_dir, identifier)

    def _read_json(self, identifier):
        status_file_path = self._status_path(identifier)
        with open(status_file_path) as status_file:
            return json.load(status_file)
    
    def _write_json(self, identifier, data):
        status_path = self._status_path(identifier)
        
        if not os.path.exists(os.path.dirname(status_path)):
            os.makedirs(os.path.dirname(status_path))
            
        with open(status_path, "w") as status_file:
            json.dump(data, status_file)


def _create_machine(*args, **kwargs):
    machine = QemuMachine(*args, **kwargs)
    return MachineWrapper(machine)


class QemuMachine(object):
    def __init__(self, users, status, statuses):
        self._users = users
        self.name = status.name
        self.image_name = status.image_name
        self.ssh_internal_port = status.ssh_internal_port
        self.identifier = status.identifier
        self._process_set = processes.from_dir(status.process_set_run_dir)
        self._forwarded_ports = status.forwarded_ports
        self._statuses = statuses
    
    def is_running(self):
        return self._process_set.all_running()
    
    def destroy(self):
        self._process_set.kill_all()
        
        wait.wait_until_not(
            self._process_set.any_running, timeout=10, wait_time=0.1,
            error_message="Failed to kill VM {0}".format(self.identifier)
        )
        
        self._statuses.remove(self.identifier)
        
    def public_port(self, guest_port):
        return self._forwarded_ports.get(guest_port, None)
        
    def external_hostname(self):
        return starboard.find_local_hostname()
        
    def users(self):
        return self._users


class UserNetworking(object):
    def settings_for(self, image, request):
        forwarded_ports = _generate_forwarded_ports(image, request.public_ports)
        return UserNetworkSettings(forwarded_ports, [])
        
    def start_network(self):
        port = starboard.find_local_free_udp_port()
        return UserNetwork(port)
        
        
class UserNetwork(object):
    def __init__(self, port):
        self._port = port
        
    def settings_for(self, image, request):
        forwarded_ports = _generate_forwarded_ports(image, request.public_ports)
        socket_args = _generate_network_args(
            "guest-net-socket",
            "socket,mcast=230.0.0.1:{0},localaddr=127.0.0.1".format(self._port),
        )
        return UserNetworkSettings(forwarded_ports, socket_args)


class UserNetworkSettings(object):
    def __init__(self, forwarded_ports, extra_args):
        self.forwarded_ports = forwarded_ports
        self._extra_args = extra_args
        
    def qemu_args(self):
        kvm_forward_ports = [
            "hostfwd=tcp::{0}-:{1}".format(host_port, guest_port)
            for guest_port, host_port
            in self.forwarded_ports.iteritems()
        ]
        return _generate_network_args(
            "guest-net-user",
            "user,{0}".format(",".join(kvm_forward_ports))
        ) + self._extra_args


def _generate_network_args(name, netdev):
    mac_address_parts = [0x06] + [random.randint(0x00, 0xff) for i in range(5)]
    mac_address = ":".join("{0:02x}".format(part) for part in mac_address_parts)
    return [
        "-netdev", "{0},id={1}".format(netdev, name),
        "-device", "virtio-net-pci,netdev={0},mac={1}".format(name, mac_address),
    ]

    
def _generate_forwarded_ports(image, public_ports):
    public_ports = set([image.ssh_internal_port] + public_ports)
    host_ports = starboard.find_local_free_tcp_ports(len(public_ports))
    return dict(zip(public_ports, host_ports))
