from .. import wait
from ..windows import netsh


def network_config(operating_system_family, shell):
    configs = {
        "linux": LinuxNetworkConfig(),
        "windows": WindowsNetworkConfig()
    }
    return NetworkConfigurer(configs[operating_system_family], shell)


class NetworkConfigurer(object):
    def __init__(self, config, shell):
        self._config = config
        self._shell = shell
        
    def add_hosts_entry(self, ip_address, hostname):
        # TODO: properly escape hosts_path
        sh_command = "echo {0} {1} >> '{2}'".format(
            ip_address, hostname, self._config.hosts_path
        )
        self._shell.run(["sh", "-c", sh_command])

    def configure_internal_interface(self, ip_address, netmask):
        return self._config.configure_internal_interface(self._shell, ip_address, netmask)


class LinuxNetworkConfig(object):
    hosts_path = "/etc/hosts"
    
    def configure_internal_interface(self, root_shell, ip_address, netmask):
        root_shell.run(["ifconfig", "eth1", ip_address, "netmask", netmask])
        
        
class WindowsNetworkConfig(object):
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    
    def configure_internal_interface(self, root_shell, ip_address, netmask):
        internal_interface_name = wait.wait_until(
            lambda: self._find_internal_interface_name(root_shell),
            timeout=30, wait_time=0.5
        )
        root_shell.run([
            "netsh", "interface", "ip", "set", "address",
            internal_interface_name, "static", ip_address, netmask
        ])
        
    def _find_internal_interface_name(self, root_shell):
        # The internal network has no DHCP server
        interfaces = netsh.interface_ip_show_config(root_shell)
        real_interfaces_without_dhcp = (
            interface.name
            for interface in interfaces
            if not interface.is_loopback and not interface.has_dhcp_lease
        )
        return next(real_interfaces_without_dhcp, None)
        
