import re

from .. import wait


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
        for interface_name in self._find_interface_names(root_shell):
            config_result = root_shell.run([
                "netsh", "interface", "ip", "show", "config",
                "name={0}".format(interface_name)
            ])
            dhcp_search_regex = r"DNS servers configured through DHCP:\s+None"
            if re.search(dhcp_search_regex, config_result.output):
                return interface_name
        
    def _find_interface_names(self, root_shell):
        field_separator_regex = re.compile("\s{2,}")
        show_interfaces_output = root_shell.run([
            "netsh", "interface", "ip", "show", "interface"
        ]).output
        lines = [
            line.strip()
            for line in show_interfaces_output.split("\n")
            if re.search(r"[^\s\-]", line)
        ]
        headers = field_separator_regex.split(lines[0])
        name_column_index = headers.index("Name")
        
        interface_names = [
            field_separator_regex.split(line)[name_column_index]
            for line in lines[1:] # Skip headers
        ]
        
        return filter(
            lambda name: "loopback" not in name.lower(),
            interface_names
        )
