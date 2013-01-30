import os
import uuid
import time
import json
import errno
import itertools
import random
import re

import spur
import spur.ssh
import starboard

from . import wait
from .users import User
from .machines import MachineWrapper
from . import processes
from . import dictobj
from .sshconfig import SshConfig

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
    invoker = QemuInvoker(command, accel_arg, images)
    statuses = Statuses(os.path.join(data_dir, "status"))
    return Provider(invoker, networking, statuses)


def _find_qemu_command():
    for command in ["qemu", "kvm"]:
        if local_shell.run(["which", command], allow_error=True).return_code == 0:
            return command
    raise RuntimeError("Could not find qemu")


class Provider(object):
    def __init__(self, invoker, networking, statuses):
        self._invoker = invoker
        self._networking = networking
        self._statuses = statuses
    
    def start(self, image_name, public_ports=None, timeout=None):
        identifier = str(uuid.uuid4())
        public_ports = set([_GUEST_SSH_PORT] + (public_ports or []))
        forwarded_ports = self._generate_forwarded_ports(public_ports)
        
        process_set = processes.start({})
        # TODO: kill processes started by network if exception is raised
        network = self._networking.start(forwarded_ports, process_set)
        self._invoker.start_process(image_name, network, process_set)
        
        status = MachineStatus(
            identifier=identifier,
            image_name=image_name,
            forwarded_ports=forwarded_ports,
            timeout=timeout,
            start_time=time.time(),
            process_set_run_dir=process_set.run_dir
        )
        
        self._statuses.write(status)
        machine = _create_machine(status, self._statuses)
        
        try:
            self._wait_for_ssh_on_machine(process_set, machine)
            return machine
        except:
            machine.destroy()
            raise
    
    def start_many(self, requests):
        # TODO: at the moment, process_set is shared between all machines,
        # meaning the destruction of one machine destroys them all
        process_set = processes.start({})
        try:
            host_ports_for_ssh = starboard.find_local_free_tcp_ports(len(requests))
            # networking.start_many needs to assign each public port on the host
            # to be forwarded to port 22 on each of the guests, the IPs of which
            # should be assigned consecutively by DHCP
            network = self._networking.start_many(host_ports_for_ssh, process_set)
            
            statuses = []
            
            for request in requests:
                identifier = str(uuid.uuid4())
                mac_address_parts = [0x06] + [random.randint(0x00, 0xff) for i in range(5)]
                mac_address = ":".join("{0:02x}".format(part) for part in mac_address_parts)
                self._invoker.start_process(request.image_name, mac_address, network, process_set)
                
                status = MachineStatus(
                    identifier=identifier,
                    image_name=request.image_name,
                    forwarded_ports={},
                    timeout=request.timeout,
                    start_time=time.time(),
                    process_set_run_dir=process_set.run_dir,
                    mac_address=mac_address,
                )
                
                self._statuses.write(status)
                statuses.append(status)
        
            for host_port_for_ssh in host_ports_for_ssh:
                print host_port_for_ssh
                ssh_config = SshConfig(
                    hostname="127.0.0.1",
                    port=host_port_for_ssh,
                    user="root",
                    password="password1"
                )
                self._wait_for_ssh(process_set, ssh_config)
                shell = ssh_config.shell()
                ifconfig = _run_ifconfig(shell)
                status = next(
                    status
                    for status in statuses
                    if status.mac_address == ifconfig.mac_address
                )
                # TODO: create separate objects to represent forwarded ports
                # to make it obvious which is guest and which is host
                status.forwarded_ports = {
                    _GUEST_SSH_PORT: host_port_for_ssh
                }
                print status.mac_address
                print ifconfig.mac_address
                print ""
                self._statuses.write(status)
        
            return MachineSet([
                _create_machine(status, self._statuses)
                for status in statuses
            ], process_set)
        except:
            process_set.kill_all()
            raise
        #~ slirp_vde_args = []
        #~ for request, machine in zip(requests, machines):
            #~ internal_ip_address = internal_ip_address_map[machine.identifier]
            #~ for guest_port in request.forward_guest_ports:
                #~ host_port = (get all free port AOT)
                #~ guest_hostname = internal_ip_address
                #~ slirp_vde_args += ["-L", "{0}:{1}:{2}".format(host_port, guest_hostname, guest_port)]
            
        # Add port forwardings for second instance of slirpvde (sans DHCP)
    
    def _generate_forwarded_ports(self, public_ports):
        return dict(
            (port, self._allocate_host_port(port))
            for port in public_ports
        )
        
    def _allocate_host_port(self, guest_port):
        return starboard.find_local_free_tcp_port()
        
    def _wait_for_ssh_on_machine(self, process_set, machine):
        return self._wait_for_ssh(process_set, machine.ssh_config("root"))
        
    def _wait_for_ssh(self, process_set, ssh_config):
        def attempt_ssh_command():
            if not process_set.all_running():
                process_set.kill_all()
                wait.wait_until_not(process_set.any_running, timeout=1, wait_time=0.1)
                output = process_set.all_output()
                raise RuntimeError("Process died, output:\n{0}".format(output))
            ssh_config.shell().run(["true"])
            
        wait.wait_until_successful(
            attempt_ssh_command,
            errors=(spur.ssh.ConnectionError, ),
            timeout=60,
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
        return _create_machine(status, self._statuses)
    
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


class MachineSet(object):
    def __init__(self, machines, process_set):
        self._machines = machines
        self._process_set = process_set
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        for machine in self._machines:
            machine.destroy()
        self._process_set.kill_all()
        
    def __getitem__(self, key):
        return self._machines[key]


class QemuInvoker(object):
    def __init__(self, command, accel_arg, images):
        self._command = command
        self._accel_arg = accel_arg
        self._images = images
        
    def start_process(self, image_name, mac_address, network, process_set):
        image_path = self._images.image_path(image_name)
        netdev_arg = network.qemu_netdev_arg()
        qemu_command = [
            self._command, "-machine", "accel={0}".format(self._accel_arg),
            "-snapshot",
            "-serial", "none",
            "-m", "512",
            "-drive", "file={0},if=virtio".format(image_path),
            "-netdev", "{0},id=guest0".format(netdev_arg),
            "-device", "virtio-net-pci,netdev=guest0,mac={0}".format(mac_address),
        ]
        print qemu_command
        process_set.start({"qemu": qemu_command})


class Images(object):
    def __init__(self, data_dir=None):
        self._data_dir = data_dir or _default_data_dir()
        
    def image_path(self, image_name):
        return os.path.join(self._data_dir, "images/{0}.qcow2".format(image_name))

    
def _default_data_dir():
    xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(xdg_data_home, "peachtree/qemu")
    

MachineStatus = dictobj.data_class("MachineStatus",
    [
        "identifier",
        "image_name",
        "forwarded_ports",
        "start_time",
        "timeout",
        "process_set_run_dir",
        "mac_address",
    ]
)


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
    _password = "password1"
    _users = [
        User("qemu-user", _password, is_root=False),
        User("root", _password, is_root=True),
    ]
    
    def __init__(self, status, statuses):
        self.image_name = status.image_name
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
        
    def hostname(self):
        return starboard.find_local_hostname()
        
    def users(self):
        return self._users


_GUEST_SSH_PORT = 22


class UserNetworking(object):
    def start(self, forwarded_ports, process_set):
        return UserNetwork(forwarded_ports)


class UserNetwork(object):
    def __init__(self, forwarded_ports):
        self._forwarded_ports = forwarded_ports
        
    def qemu_netdev_arg(self):
        kvm_forward_ports = [
            "hostfwd=tcp::{0}-:{1}".format(host_port, guest_port)
            for guest_port, host_port
            in self._forwarded_ports.iteritems()
        ]
        return "user," + ",".join(kvm_forward_ports)



class VdeNetworking(object):
    def start(self, forwarded_ports, process_set):
        switch_path = "/tmp/{0}".format(uuid.uuid4())
        process_set.start({
            "switch": ["vde_switch", "-s", switch_path]
        })
        
        def can_connect_to_switch():
            # TODO: escape switch_path
            result = local_shell.run(
                ["sh", "-c", "true | vde_plug {0}".format(switch_path)],
                allow_error=True
            )
            return result.return_code == 0
            
        wait.wait_until(
            can_connect_to_switch, timeout=10, wait_time=0.1,
            error_message="Failed to connect to vde_switch"
        )
        
        # first address assigned by default slirpvde DHCP server
        guest_hostname = "10.0.2.15" 
        port_args = list(itertools.chain(*[
            ["-L", "{0}:{1}:{2}".format(host_port, guest_hostname, guest_port)]
            for guest_port, host_port in forwarded_ports.iteritems()
        ]))
        process_set.start({
            "slirpvde": ["slirpvde", "-s", switch_path, "--dhcp"] + port_args
        })
        return VdeNetwork(switch_path)

    def start_many(self, host_ports_for_ssh, process_set):
        switch_path = "/tmp/{0}".format(uuid.uuid4())
        process_set.start({
            "switch": ["vde_switch", "-s", switch_path]
        })
        
        def can_connect_to_switch():
            # TODO: escape switch_path
            result = local_shell.run(
                ["sh", "-c", "true | vde_plug {0}".format(switch_path)],
                allow_error=True
            )
            return result.return_code == 0
            
        wait.wait_until(
            can_connect_to_switch, timeout=10, wait_time=0.1,
            error_message="Failed to connect to vde_switch"
        )
        
        # slirpvde assigns addresses from 10.0.2.15
        
        port_args = []
        for i, host_port in enumerate(host_ports_for_ssh):
            guest_hostname = "10.0.2.{0}".format(15 + i)
            port_args += ["-L", "{0}:{1}:{2}".format(host_port, guest_hostname, _GUEST_SSH_PORT)]
        print port_args
        process_set.start({
            "slirpvde": ["slirpvde", "-s", switch_path, "--dhcp"] + port_args
        })
        return VdeNetwork(switch_path)
        


class VdeNetwork(object):
    def __init__(self, switch_path):
        self._switch_path = switch_path
    
    def qemu_netdev_arg(self):
        return "vde,sock={0}".format(self._switch_path)


def _run_ifconfig(shell):
    output = shell.run(["/sbin/ifconfig", "eth0"]).output
    mac_address = re.search("HWaddr (\S+)", output).group(1).lower()
    return NetworkInterfaceConfig(mac_address)
    
    
NetworkInterfaceConfig = dictobj.data_class(
    "NetworkInterfaceConfig",
    ["mac_address"]
)
    
