import re

from .. import wait
from ..windows import netsh


def network_config(operating_system_family):
    configs = {
        "linux": LinuxNetworkConfig(),
        "windows": WindowsNetworkConfig()
    }
    return configs[operating_system_family]


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
        
