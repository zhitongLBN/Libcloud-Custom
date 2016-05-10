# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.common.base import BaseDriver
from libcloud.common.base import ConnectionKey

__all__ = [
    'NetworkingDriver'
]


class NetworkingDriver(BaseDriver):

    """
    A base NetworkingDriver class to derive from

    This class is always subclassed by a specific driver.

    """

    connectionCls = ConnectionKey
    name = None
    type = None
    port = None

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 **kwargs):
        super(NetworkingDriver, self).__init__(key=key, secret=secret,
                                               secure=secure, host=host,
                                               port=port, **kwargs)


class Firewall(object):

    def __init__(self, id, name, state, policy_id, driver,
                 description=None, extra=None, locked=None, service_type=None):
        """
        TODO

        """
        self.driver = driver
        self.id = str(id)
        self.name = name
        self.state = state
        self.policy_id = policy_id
        self.description = description or ""
        self.extra = extra or {}
        self.locked = locked or ""
        self.service_type = service_type or ""

    def __repr__(self):
        return (('<Firewall: id=%s, name=%s, state=%s, policy_id=%s, '
                 'locked=%s, service_type=%s, driver=%s ...>')
                % (self.id, self.name, self.state, self.policy_id,
                   self.locked, self.service_type, self.driver.name))


class FirewallRule(object):

    def __init__(self, id, name, protocol, ip_version,
                 source_ip_address, destination_ip_address, source_port,
                 destination_port, action, enabled, driver,
                 description=None, extra=None):
        """
        TODO

        """

        self.id = id
        self.name = name
        self.description = description or ""
        self.protocol = protocol
        self.ip_version = ip_version
        self.source_ip_address = source_ip_address
        self.destination_ip_address = destination_ip_address
        self.source_port = source_port
        self.destination_port = destination_port
        self.action = action
        self.enabled = enabled
        self.driver = driver
        self.extra = extra or {}   # Here : policy_id

    def __repr__(self):
        name = self.name.encode('utf8')
        try:
            return (('<FirewallRule: id=%s, name=%s, protocol=%s, '
                     'ip_version=%s, '
                     'source_ip_address=%s, destination_ip_address=%s, '
                     'source_port=%s, destination_port=%s, action=%s, '
                     'enabled=%s, driver=%s ...>')
                    % (self.id, name, self.protocol, self.ip_version,
                       self.source_ip_address, self.destination_ip_address,
                       self.source_port, self.destination_port, self.action,
                       self.enabled, self.driver.name))
        except Exception:
            name = ''.join([i if ord(i) < 128 else '?' for i in name])
            return (('<FirewallRule: id=%s, name=%s, protocol=%s, '
                     'ip_version=%s, '
                     'source_ip_address=%s, destination_ip_address=%s, '
                     'source_port=%s, destination_port=%s, action=%s, '
                     'enabled=%s, driver=%s ...>')
                    % (self.id, name, self.protocol, self.ip_version,
                       self.source_ip_address, self.destination_ip_address,
                       self.source_port, self.destination_port, self.action,
                       self.enabled, self.driver.name))


class FirewallPolicy(object):

    def __init__(self, id, name, firewall_rules_list,
                 shared, audited, driver, extra=None, description=None):
        """
        TODO

        """

        self.id = id
        self.name = name
        self.description = description or ""
        self.firewall_rules_list = firewall_rules_list,
        self.shared = shared
        self.audited = audited
        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        name = self.name.encode('utf8')
        try:
            return (('<FirewallPolicy: id=%s, name=%s, shared=%s, '
                     'audited=%s, driver=%s, firewall_rules_list=[...] ...>')
                    % (self.id, name, self.shared, self.audited,
                       self.driver.name))
        except Exception:
            name = ''.join([i if ord(i) < 128 else '?' for i in name])
            return (('<FirewallPolicy: id=%s, name=%s, shared=%s, '
                     'audited=%s, driver=%s, firewall_rules_list=[...] ...>')
                    % (self.id, name, self.shared, self.audited,
                       self.driver.name))


class Network(object):

    def __init__(self, id, driver, status=None, subnets=[], name=None,
                 routerext=None, tenant_id=None, admin_state_up=None,
                 shared=None):
        """
        TODO

        """
        self.status = status
        self.subnets = subnets
        self.name = name
        self.routerext = routerext
        self.tenant_id = tenant_id
        self.admin_state_up = admin_state_up
        self.shared = shared
        self.id = id
        self.driver = driver

    def __repr__(self):
        try:
            return (('<Network: id=%s, name=%s, status=%s, '
                     'router:external=%s, admin_state_up=%s, shared=%s,'
                     'subnets=[...] ...>')
                    % (self.id, self.name, self.status, self.routerext,
                       self.admin_state_up, self.shared,))
        except Exception as e:
            raise e


class Subnet(object):

    def __init__(self, name, enable_dhcp, network_id, tenant_id,
                 dns_nameservers, driver, allocation_pools, host_routes,
                 ip_version, gateway_ip, cidr, id):
        self.name = name
        self.enable_dhcp = enable_dhcp
        self.network_id = network_id
        self.tenant_id = tenant_id
        self.dns_nameservers = dns_nameservers
        self.allocation_pools = allocation_pools
        self.host_routes = host_routes
        self.ip_version = ip_version
        self.gateway_ip = gateway_ip
        self.cidr = cidr
        self.id = id
        self.driver = driver

    def __repr__(self):
        try:
            return (('<Subnet: id=%s, name=%s, cidr=%s, '
                     'network_id=%s, ip_version=%s, gateway_ip=%s, '
                     'dns_nameservers=[...], allocation_pools=[...], '
                     'host_routes=[...] ...>')
                    % (self.id, self.name, self.cidr, self.network_id,
                       self.ip_version, self.gateway_ip,))
        except Exception as e:
            raise e


class Port(object):

    def __init__(self, status, name, admin_state_up, network_id,
                 tenant_id, device_owner, mac_address, driver, fixed_ips,
                 id, security_groups, device_id):
        self.status = status
        self.name = name
        self.admin_state_up = admin_state_up
        self.network_id = network_id
        self.tenant_id = tenant_id
        self.device_owner = device_owner
        self.mac_address = mac_address
        self.fixed_ips = fixed_ips
        self.id = id
        self.security_groups = security_groups
        self.device_id = device_id
        self.driver = driver

    def __repr__(self):
        try:
            return (('<Port: id=%s, name=%s, admin_state_up=%s, '
                     'network_id=%s, device_owner=%s, device_id=%s, '
                     ' mac_address=%s, fixed_ips=[...]'
                     ' security_groups=[...] ...>')
                    % (self.id, self.name, self.admin_state_up,
                       self.network_id, self.device_owner, self.device_id,
                       self.mac_address,))
        except Exception as e:
            raise e
