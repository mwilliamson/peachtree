import re


def interface_ip_show_config(shell):
    result = shell.run(["netsh", "interface", "ip", "show", "config"])
    return read_interface_ip_show_config(result.output)

    
def read_interface_ip_show_config(output):
    interface_blocks = [
        block.strip()
        for block in re.split(r"\n\s*\n", output)
        if block.strip()
    ]
    
    return map(_read_interface_block, interface_blocks)
    
def _read_interface_block(interface_block):
    lines = [line.rstrip() for line in interface_block.split("\n")]
    name_match_result = re.match(
        'Configuration for interface "([^"]*)"',
        lines[0]
    )
    name = name_match_result.group(1)
    has_dhcp_lease = _read_has_dhcp_lease(lines)
    return Interface(name, has_dhcp_lease)

    
def _is_interface_header(line):
    return line.strip() and not _is_property_line(line)


def _read_has_dhcp_lease(lines):
    properties = _read_properties(lines)
    dhcp_enabled = properties["DHCP enabled"].lower()
    if dhcp_enabled == "no":
        return False
    elif dhcp_enabled == "yes":
        dns_configured_by_dhcp = \
            properties["DNS servers configured through DHCP"]
        return dns_configured_by_dhcp.lower() != "none"
    else:
        raise Exception("Unknown value for DHCP enabled: {0}".format(dhcp_enabled))
        
        
def _read_properties(lines):
    property_lines = filter(_is_property_line, lines)
    return dict(
        re.split(r":\s*", line.strip(), 1)
        for line in property_lines
    )
    

def _is_property_line(line):
    return re.match(r"^\s+\S", line)


class Interface(object):
    def __init__(self, name, has_dhcp_lease):
        self.name = name
        self.has_dhcp_lease = has_dhcp_lease
        
    @property
    def is_loopback(self):
        return "loopback" in self.name.lower()
