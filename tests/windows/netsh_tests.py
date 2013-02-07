from nose.tools import istest, assert_equal

from peachtree.windows import netsh


@istest
def can_read_empty_list_of_interfaces():
    netsh_output = """
    
"""
    interfaces = netsh.read_interface_ip_show_config(netsh_output)
    assert_equal([], interfaces)


@istest
def can_read_configuration_for_each_interface():
    netsh_output = """
Configuration for interface "Local Area Connection"
    DHCP enabled:                         Yes
    IP Address:                           10.0.2.15
    Subnet Prefix:                        10.0.2.0/24 (mask 255.255.255.0)
    Default Gateway:                      10.0.2.2
    Gateway Metric:                       0
    InterfaceMetric:                      5
    DNS servers configured through DHCP:  10.0.2.3
    Register with which suffix:           Primary only
    WINS servers configured through DHCP: None

Configuration for interface "Local Area Connection 2"
    DHCP enabled:                         Yes
    IP Address:                           10.0.2.15
    Subnet Prefix:                        10.0.2.0/24 (mask 255.255.255.0)
    Default Gateway:                      10.0.2.2
    Gateway Metric:                       0
    InterfaceMetric:                      5
    DNS servers configured through DHCP:  None
    Register with which suffix:           Primary only
    WINS servers configured through DHCP: None

Configuration for interface "Loopback Pseudo-Interface 1"
    DHCP enabled:                         No
    IP Address:                           127.0.0.1
    Subnet Prefix:                        127.0.0.0/8 (mask 255.0.0.0)
    InterfaceMetric:                      50
    Statically Configured DNS Servers:    None
    Register with which suffix:           Primary only
    Statically Configured WINS Servers:   None

"""
    interfaces = netsh.read_interface_ip_show_config(netsh_output)
    assert_equal(3, len(interfaces))
    
    assert_equal("Local Area Connection", interfaces[0].name)
    assert_equal("Local Area Connection 2", interfaces[1].name)
    assert_equal("Loopback Pseudo-Interface 1", interfaces[2].name)
    
    assert interfaces[0].has_dhcp_lease
    assert not interfaces[1].has_dhcp_lease
    assert not interfaces[2].has_dhcp_lease


@istest
def interface_is_loopback_if_name_contains_loopback():
    assert not netsh.Interface("Local Area Connection", False).is_loopback
    assert netsh.Interface("Loopback Pseudo-Interface 1", False).is_loopback
    assert netsh.Interface("loopback Pseudo-Interface 1", False).is_loopback
