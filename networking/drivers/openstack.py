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

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.common.openstack import OpenStackDriverMixin
from libcloud.common.openstack import OpenStackBaseConnection
from libcloud.common.openstack import OpenStackResponse
from libcloud.networking.base import Firewall, FirewallRule, FirewallPolicy
from libcloud.networking.base import Network, Subnet, Port
from libcloud.networking.base import NetworkingDriver
from libcloud.utils.py3 import httplib

DEFAULT_VERSION = "v1"

__all__ = [
    'OpenstackNetworkingDriver',
    'OpenStackNetworkingConnection',
    'OpenStack_Connection',
    'OpenStack_Response'
]


class OpenStack_Response(OpenStackResponse):
    def __init__(self, *args, **kwargs):
        # done because of a circular reference from
        # NodeDriver -> Connection -> Response
        self.network_driver = OpenstackNetworkingDriver
        super(OpenStack_Response, self).__init__(*args, **kwargs)


class OpenStackNetworkingConnection(OpenStackBaseConnection):
    # default config for http://cloud.numergy.com/
    service_type = 'network'
    service_name = 'neutron'
    service_region = 'tr2'


class OpenStack_Connection(OpenStackNetworkingConnection):
    responseCls = OpenStack_Response
    accept_format = 'application/json'
    default_content_type = 'application/json; charset=UTF-8'

    def encode_data(self, data):
        return json.dumps(data)


class OpenstackNetworkingDriver(NetworkingDriver, OpenStackDriverMixin):
    """
    Base OpenStack networking driver.
    """
    api_name = 'openstack'
    name = 'OpenStack'
    website = 'http://openstack.org/'
    connectionCls = OpenStack_Connection

    def __init__(self, *args, **kwargs):
        OpenStackDriverMixin.__init__(self, **kwargs)
        self._ex_force_api_version = str(kwargs.pop('ex_force_api_version',
                                                    None))
        super(OpenstackNetworkingDriver, self).__init__(*args, **kwargs)

    def _ex_connection_class_kwargs(self):
        return self.openstack_connection_kwargs()

    def list_firewalls(self):
        return self._to_firewalls(self.connection.request(
                                        '/fw/firewalls').object)

    def get_firewall_detail(self, firewall_id):
        """
        Lists details of the specified firewall.

        :param       firewall_id: ID of the firewall which should be used
        :type        firewall_id: ``str``

        :rtype: :class:`Firewall`
        """
        if isinstance(firewall_id, Firewall):
            firewall_id = firewall_id.id

        uri = '/fw/firewalls/%s' % (firewall_id)
        resp = self.connection.request(uri, method='GET')
        if resp.status == httplib.NOT_FOUND:
            return None

        return self._to_firewall(resp.object["firewall"])

    def _to_firewalls(self, obj):
        return [self._to_firewall(firewall) for firewall in obj['firewalls']]

    def _to_firewall(self, obj):
        f = Firewall(id=obj.get('id'),
                     name=obj.get('name'),
                     state=obj.get('status'),
                     policy_id=obj.get('firewall_policy_id'),
                     driver=self.connection.driver,
                     description=obj.get('description'),
                     locked=obj.get('locked'),
                     service_type=obj.get('service_type'),
                     extra={
                            'admin_state_up': obj.get('admin_state_up')
                            })

        return f

    def create_firewall(self, admin_state_up, policy_id, name):
        data = {"firewall": {
                    "admin_state_up": admin_state_up,
                    "firewall_policy_id": policy_id,
                    "name": name}}

        ret = self.connection.request('/fw/firewalls',
                                      method='POST', data=data).object
        return ret

    def _create_args_to_firewall_params(self, **kwargs):
        firewall_params = {}

        if 'admin_state_up' in kwargs:
            firewall_params['admin_state_up'] = kwargs['admin_state_up']

        if 'description' in kwargs:
            firewall_params['description'] = kwargs['description']

        if 'firewall_policy_id' in kwargs:
            firewall_params['firewall_policy_id'] = kwargs[
                                                        'firewall_policy_id']

        if 'name' in kwargs:
            firewall_params['name'] = kwargs['name']

        return firewall_params

    def update_firewall(self, firewall, **updates):
        params = self._create_args_to_firewall_params(**updates)
        data = {"firewall": params}
        ret = self.connection.request('/fw/firewalls/%s' % (firewall.id,),
                                      method='PUT', data=data).object
        return ret

    def delete_firewall(self, firewall):
        resp = self.connection.request('/fw/firewalls/%s' % (firewall.id,),
                                       method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def list_firewall_rules(self):
        return self._to_firewall_rules(self.connection.request(
                                        '/fw/firewall_rules').object)

    def get_firewall_rule_detail(self, rule_id):
        """
        Lists details of the specified firewall rule.

        :param       rule_id: ID of the firewall rule which should be used
        :type        rule_id: ``str``

        :rtype: :class:`Firewall Rule`
        """
        if isinstance(rule_id, FirewallRule):
            rule_id = rule_id.id

        uri = '/fw/firewall_rules/%s' % (rule_id)
        resp = self.connection.request(uri, method='GET')
        if resp.status == httplib.NOT_FOUND:
            return None
        return self._to_firewall_rule(resp.object["firewall_rule"])

    def _to_firewall_rules(self, obj):
        return [self._to_firewall_rule(
                    firewall_rule) for firewall_rule in obj['firewall_rules']]

    def _to_firewall_rule(self, obj):
        fr = FirewallRule(id=obj.get('id'),
                          name=obj.get('name'),
                          protocol=obj.get('protocol'),
                          ip_version=obj.get('ip_version'),
                          source_ip_address=obj.get('source_ip_address'),
                          destination_ip_address=obj.get(
                                                'destination_ip_address'),
                          source_port=obj.get('source_port'),
                          destination_port=obj.get('destination_port'),
                          action=obj.get('action'),
                          enabled=obj.get('enabled'),
                          driver=self.connection.driver,
                          description=obj.get('description'),
                          extra={
                        'firewall_policy_id': obj.get('firewall_policy_id'),
                        'shared': obj.get('shared'),
                        'position': obj.get('position')
                                })
        return fr

    def create_firewall_rule(self, **kwargs):
        params = self._create_args_to_firewall_rule(**kwargs)
        data = {
                    "firewall_rule": params
                }
        ret = self.connection.request('/fw/firewall_rules',
                                      method='POST', data=data).object
        if 'firewall_rule' in ret:
            return self._to_firewall_rule(ret['firewall_rule'])
        return ret

    def update_firewall_rule(self, firewall_rule, **kwargs):
        params = self._create_args_to_firewall_rule(**kwargs)
        data = {"firewall_rule": params}
        ret = self.connection.request('/fw/firewall_rules/%s' %
                                      (firewall_rule.id,),
                                      method='PUT', data=data).object
        return ret

    def _create_args_to_firewall_rule(self, **kwargs):
        firewall_rule = {}

        if 'action' in kwargs:
            if not (kwargs['action'] is None):

                firewall_rule['action'] = kwargs['action']

        if 'description' in kwargs:
            if not (kwargs['description'] is None):
                firewall_rule['description'] = kwargs['description']

        if 'destination_ip_address' in kwargs:
            if not (kwargs['destination_ip_address'] is None):
                firewall_rule['destination_ip_address'] = \
                                        kwargs['destination_ip_address']

        if 'destination_port' in kwargs:
            if not (kwargs['destination_port'] is None):
                firewall_rule['destination_port'] = kwargs['destination_port']

        if 'enabled' in kwargs:
            if not (kwargs['enabled'] is None):
                firewall_rule['enabled'] = kwargs['enabled']

        if 'ip_version' in kwargs:
            if not (kwargs['ip_version'] is None):
                firewall_rule['ip_version'] = kwargs['ip_version']

        if 'name' in kwargs:
            if not (kwargs['name'] is None):
                firewall_rule['name'] = kwargs['name']

        if 'protocol' in kwargs:
            if not (kwargs['protocol'] is None):
                firewall_rule['protocol'] = kwargs['protocol']

        if 'shared' in kwargs:
            if not (kwargs['shared'] is None):
                firewall_rule['shared'] = kwargs['shared']

        if 'source_ip_address' in kwargs:
            if not (kwargs['source_ip_address'] is None):
                firewall_rule['source_ip_address'] = kwargs[
                                                    'source_ip_address']

        if 'source_port' in kwargs:
            if not (kwargs['source_port'] is None):
                firewall_rule['source_port'] = kwargs['source_port']

        return firewall_rule

    def delete_firewall_rule(self, firewall_rule):
        resp = self.connection.request('/fw/firewall_rules/%s' %
                                       (firewall_rule.id,),
                                       method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def list_firewall_policies(self):
        return self._to_firewall_policies(self.connection.request(
                                        '/fw/firewall_policies').object)

    def get_firewall_policy_detail(self, policy_id):
        """
        Lists details of the specified firewall rule.

        :param       policy_id: ID of the firewall policy which should be used
        :type        policy_id: ``str``

        :rtype: :class:`Firewall Policy`
        """
        if isinstance(policy_id, FirewallPolicy):
            policy_id = policy_id.id

        uri = '/fw/firewall_policies/%s' % (policy_id)
        resp = self.connection.request(uri, method='GET')
        if resp.status == httplib.NOT_FOUND:
            return None

        return self._to_firewall_policy(resp.object["firewall_policy"])

    def _to_firewall_policies(self, obj):
        return [self._to_firewall_policy(
                            firewall_policy) for firewall_policy in obj[
                                                'firewall_policies']]

    def _to_firewall_policy(self, obj):
        fp = FirewallPolicy(id=obj.get('id'),
                            name=obj.get('name'),
                            firewall_rules_list=obj.get('firewall_rules'),
                            shared=obj.get('shared'),
                            audited=obj.get('audited'),
                            driver=self.connection.driver,
                            extra={},
                            description=obj.get('description'))
        return fp

    def create_firewall_policy(self, name, firewall_rules_list):
        l = []
        for firewall_rule in firewall_rules_list:
            l.append(firewall_rule.id)
        data = {
                "firewall_policy": {
                    "firewall_rules": l,
                    "name": name
                }
             }
        ret = self.connection.request('/fw/firewall_policies',
                                      method='POST', data=data).object
        if 'firewall_policy' in ret:
            return self._to_firewall_policy(ret['firewall_policy'])
        return ret

    def update_firewall_policy(self, firewall_policy, **updates):
        params = self._create_args_to_firewall_policy_params(**updates)
        data = {"firewall_policy": params}
        ret = self.connection.request('/fw/firewall_policies/%s' %
                                      (firewall_policy.id,),
                                      method='PUT', data=data).object
        return ret

    def delete_firewall_policy(self, firewall_policy):
        resp = self.connection.request('/fw/firewall_policies/%s' %
                                       (firewall_policy.id,),
                                       method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def remove_rule(self, firewall_policy, firewall_rule):
        data = {
                    "firewall_rule_id": firewall_rule.id
                }
        ret = self.connection.request('/fw/firewall_policies/%s/remove_rule' %
                                      (firewall_policy.id,),
                                      method='PUT', data=data).object
        return ret

    def insert_rule(self, firewall_policy, firewall_rule):
        data = {
                    "firewall_rule_id": firewall_rule.id,
                    "insert_after": "",
                    "insert_before": ""
                }
        ret = self.connection.request('/fw/firewall_policies/%s/insert_rule' %
                                      (firewall_policy.id,),
                                      method='PUT', data=data).object
        return ret

    def _create_args_to_firewall_policy_params(self, **kwargs):
        firewallpolicy_params = {}

        if 'firewall_rules_list' in kwargs:
            l = []
            for firewall_rule in kwargs['firewall_rules_list']:
                l.append(firewall_rule.id)
            firewallpolicy_params['firewall_rules'] = l

        if 'name' in kwargs:
            if not (kwargs['name'] is None):
                firewallpolicy_params['name'] = kwargs['name']

        if 'description' in kwargs:
            if not (kwargs['description'] is None):
                firewallpolicy_params['description'] = kwargs['description']

        if 'audited' in kwargs:
            if not (kwargs['audited'] is None):
                firewallpolicy_params['audited'] = kwargs['audited']

        if 'shared' in kwargs:
            if not (kwargs['shared'] is None):
                firewallpolicy_params['shared'] = kwargs['shared']

        return firewallpolicy_params

    def list_networks(self):
        return self._to_networks(self.connection.request('/networks').object)

    def _to_networks(self, obj):
        return [self._to_network(
                            network) for network in obj[
                                                'networks']]

    def _to_network(self, obj):
        netw = Network(id=obj.get('id'),
                       subnets=obj.get('subnets'),
                       name=obj.get('name'),
                       routerext=obj.get('routerext'),
                       tenant_id=obj.get('tenant_id'),
                       driver=self.connection.driver,
                       shared=obj.get('shared'),
                       admin_state_up=obj.get('admin_state_up'))
        return netw

    def create_network(self, **kwargs):
        params = self._create_args_to_network_params(**kwargs)
        data = {"network": params}

        ret = self.connection.request('/networks',
                                      method='POST', data=data).object
        if 'network' in ret:
            return self._to_network(ret['network'])
        return ret

    def _create_args_to_network_params(self, **kwargs):
        network_params = {}

        if 'admin_state_up' in kwargs:
            if not (kwargs['admin_state_up'] is None):
                network_params['admin_state_up'] = kwargs['admin_state_up']

        if 'name' in kwargs:
            if not (kwargs['name'] is None):
                network_params['name'] = kwargs['name']

        if 'shared' in kwargs:
            if not (kwargs['shared'] is None):
                network_params['shared'] = kwargs['shared']

        if 'tenant_id' in kwargs:
            if not (kwargs['tenant_id'] is None):
                network_params['tenant_id'] = kwargs['tenant_id']

        return network_params

    def delete_network(self, network):
        resp = self.connection.request('/networks/%s' %
                                       (network.id,),
                                       method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def list_subnets(self):
        return self._to_subnets(self.connection.request('/subnets').object)

    def create_subnet(self, network_id, ip_version, cidr, **kwargs):
        data = {"subnet": {
                            "network_id": network_id,
                            "ip_version": ip_version,
                            "cidr": cidr
                          }
                }
        params = self._create_args_to_subnet_params(**kwargs)
        data['subnet'].update(params)
        ret = self.connection.request('/subnets',
                                      method='POST', data=data).object
        if 'subnet' in ret:
            return self._to_subnet(ret['subnet'])
        return ret

    def delete_subnet(self, subnet):
        resp = self.connection.request('/subnets/%s' %
                                       (subnet.id,),
                                       method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def get_subnet_detail(self, sub_id):
        """
        Lists details of the specified subnet.

        :param       sub_id: ID of the subnet which should be used
        :type        sub_id: ``str``

        :rtype: :class:`Subnet`
        """
        if isinstance(sub_id, Subnet):
            sub_id = sub_id.id

        uri = '/subnets/%s' % (sub_id)
        resp = self.connection.request(uri, method='GET')
        if resp.status == httplib.NOT_FOUND:
            return None

        return self._to_subnet(resp.object["subnet"])

    def _create_args_to_subnet_params(self, **kwargs):
        subnet_params = {}

        if 'name' in kwargs:
            subnet_params['name'] = kwargs['name']

        if 'tenant_id' in kwargs:
            subnet_params['tenant_id'] = kwargs['tenant_id']

        if 'allocation_pools' in kwargs:
            subnet_params['allocation_pools'] = kwargs['allocation_pools']

        if 'start' in kwargs:
            subnet_params['start'] = kwargs['start']

        if 'end' in kwargs:
            subnet_params['end'] = kwargs['end']

        if 'gateway_ip' in kwargs:
            subnet_params['gateway_ip'] = kwargs['gateway_ip']

        if 'enable_dhcp' in kwargs:
            subnet_params['enable_dhcp'] = kwargs['enable_dhcp']

        if 'dns_nameservers' in kwargs:
            subnet_params['dns_nameservers'] = kwargs['dns_nameservers']

        if 'host_routes' in kwargs:
            subnet_params['host_routes'] = kwargs['host_routes']

        if 'destination' in kwargs:
            subnet_params['destination'] = kwargs['destination']

        if 'nexthop' in kwargs:
            subnet_params['nexthop'] = kwargs['nexthop']

        if 'ipv6_ra_mode' in kwargs:
            subnet_params['ipv6_ra_mode'] = kwargs['ipv6_ra_mode']

        if 'ipv6_address_mode' in kwargs:
            subnet_params['ipv6_address_mode'] = kwargs[
                                                    'ipv6_address_mode']

        return subnet_params

    def _to_subnets(self, obj):
        return [self._to_subnet(
                            subnet) for subnet in obj[
                                                'subnets']]

    def _to_subnet(self, obj):
        subn = Subnet(id=obj.get('id'),
                      name=obj.get('name'),
                      enable_dhcp=obj.get(' enable_dhcp'),
                      network_id=obj.get(' network_id'),
                      tenant_id=obj.get('tenant_id'),
                      dns_nameservers=obj.get('dns_nameservers'),
                      allocation_pools=obj.get('allocation_pools'),
                      host_routes=obj.get('host_routes'),
                      ip_version=obj.get('ip_version'),
                      gateway_ip=obj.get(' gateway_ip'),
                      cidr=obj.get('cidr'),
                      driver=self.connection.driver)
        return subn

    def list_ports(self):
        return self._to_ports(self.connection.request('/ports').object)

    def _to_ports(self, obj):
        return [self._to_port(
                            port) for port in obj[
                                                'ports']]

    def create_port(self, network_id, **kwargs):
        data = {"port": {
                            "network_id": network_id
                          }
                }
        params = self._create_args_to_port_params(**kwargs)
        data['port'].update(params)
        ret = self.connection.request('/ports',
                                      method='POST', data=data).object
        if 'port' in ret:
            return self._to_port(ret['port'])
        return ret

    def _create_args_to_port_params(self, **kwargs):
        port_params = {}

        if 'name' in kwargs:
            port_params['name'] = kwargs['name']

        if 'admin_state_up' in kwargs:
            port_params['admin_state_up'] = kwargs['admin_state_up']

        if 'tenant_id' in kwargs:
            port_params['tenant_id'] = kwargs['tenant_id']

        if 'mac_address' in kwargs:
            port_params['mac_address'] = kwargs['mac_address']

        if 'fixed_ips' in kwargs:
            port_params['fixed_ips'] = kwargs['fixed_ips']

        if 'subnet_id' in kwargs:
            port_params['subnet_id'] = kwargs['subnet_id']

        if 'ip_address' in kwargs:
            port_params['ip_address'] = kwargs['ip_address']

        if 'security_groups' in kwargs:
            port_params['security_groups'] = kwargs['security_groups']

        if 'allowed_address_pairs' in kwargs:
            port_params['allowed_address_pairs'] = kwargs[
                                                'allowed_address_pairs']

        if 'ip_address' in kwargs:
            port_params['ip_address'] = kwargs['ip_address']

        if 'mac_address' in kwargs:
            port_params['mac_address'] = kwargs['mac_address']

        if 'opt_value' in kwargs:
            port_params['opt_value'] = kwargs['opt_value']

        if 'opt_name' in kwargs:
            port_params['opt_name'] = kwargs['opt_name']

        if 'device_owner' in kwargs:
            port_params['device_owner'] = kwargs['device_owner']

        if 'device_id' in kwargs:
            port_params['device_id'] = kwargs['device_id']

        return port_params

    def delete_port(self, port):
        resp = self.connection.request('/ports/%s' %
                                       (port.id,),
                                       method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def _to_port(self, obj):

        port = Port(status=obj.get("status"),
                    name=obj.get("name"),
                    admin_state_up=obj.get("admin_state_up"),
                    network_id=obj.get("network_id"),
                    tenant_id=obj.get("tenant_id"),
                    device_owner=obj.get("device_owner"),
                    mac_address=obj.get("mac_address"),
                    fixed_ips=obj.get("fixed_ips"),
                    id=obj.get("id"),
                    security_groups=obj.get("security_groups"),
                    device_id=obj.get("device_id"),
                    driver=self.connection.driver)
        return port
