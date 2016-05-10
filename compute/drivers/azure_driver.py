# -*- coding: utf8 -*-
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
"""Azure Compute driver

"""

# from azure import
import random

try:
    from azure import (
        WindowsAzureMissingResourceError)
    from azure.servicemanagement import ServiceManagementService
    from azure.servicemanagement import OSVirtualHardDisk
    from azure.servicemanagement import LinuxConfigurationSet
    from azure.servicemanagement import WindowsConfigurationSet
    from azure.servicemanagement import ConfigurationSet
    from azure.servicemanagement import ConfigurationSetInputEndpoint
except ImportError:
    raise ImportError('Missing "azure" dependency. You can install it '
                      'using pip - azure install azure')

# from libcloud.utils.py3 import urlquote as url_quote

from libcloud.compute.providers import Provider
from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation
# from libcloud.compute.base import StorageVolume
from libcloud.compute.types import NodeState
# from libcloud.common.types import LibcloudError


class AzureNodeDriver(NodeDriver):
    name = "Azure Node Provider"
    type = Provider.AZURE
    website = 'http://windowsazure.com'
    sms = None

    rolesizes = None

    NODE_STATE_MAP = {
        'RoleStateUnknown': NodeState.UNKNOWN,
        'CreatingVM': NodeState.PENDING,
        'StartingVM': NodeState.PENDING,
        'CreatingRole': NodeState.PENDING,
        'StartingRole': NodeState.PENDING,
        'ReadyRole': NodeState.RUNNING,
        'BusyRole': NodeState.PENDING,
        'StoppingRole': NodeState.PENDING,
        'StoppingVM': NodeState.PENDING,
        'DeletingVM': NodeState.PENDING,
        'StoppedVM': NodeState.STOPPED,
        'RestartingRole': NodeState.REBOOTING,
        'CyclingRole': NodeState.TERMINATED,
        'FailedStartingRole': NodeState.TERMINATED,
        'FailedStartingVM': NodeState.TERMINATED,
        'UnresponsiveRole': NodeState.TERMINATED,
        'StoppedDeallocated': NodeState.TERMINATED,
    }

    def __init__(self, subscription_id=None, key_file=None, **kwargs):
        """
        subscription_id contains the Azure subscription id
        in the form of GUID key_file contains
        the Azure X509 certificate in .pem form
        """
        self.subscription_id = subscription_id
        self.key_file = key_file
        self.sms = ServiceManagementService(subscription_id, key_file)

        super(AzureNodeDriver, self).__init__(
            self.subscription_id,
            self.key_file,
            secure=True,
            **kwargs)

    def list_sizes(self):
        """
        Lists all sizes from azure

        :rtype: ``list`` of :class:`NodeSize`
        """
        if self.rolesizes is None:
            # refresh rolesizes
            data = self.sms.list_role_sizes()
            self.rolesizes = [self._to_node_size(i) for i in data]
        return self.rolesizes

    def list_images(self, location=None):
        """
        Lists all sizes from azure

        :rtype: ``list`` of :class:`NodeSize`
        """
        data = self.sms.list_os_images()
        images = [self._to_image(i) for i in data]

        if location is not None:
            images = [image for image in images
                      if location in image.extra["location"]]
        return images

    def list_locations(self):
        """
        Lists all Location from azure

        :rtype: ``list`` of :class:`NodeLocation`
        """
        data = self.sms.list_locations()
        locations = [self._to_location(i) for i in data]
        return locations

    def list_virtual_net(self):
        """
        List all VirtualNetworkSites

        :rtype: ``list`` of :class:`VirtualNetwork`
        """
        data = self.sms.list_virtual_network_sites()
        virtualnets = [self._to_virtual_network(i) for i in data]
        return virtualnets

    def create_node(self,
                    name,
                    image,
                    size,
                    storage,
                    service_name,
                    vm_user,
                    vm_password,
                    location=None,
                    affinity_group=None,
                    virtual_network=None):
        """
        Create a vm deploiement request

        :rtype:  :class:`.Node`
        :return: ``Node`` Node instance on success.
        """

        try:
            self.sms.get_hosted_service_properties(service_name)
            pass
        except WindowsAzureMissingResourceError:
            # create cloud service
            if bool(location is not None) != bool(affinity_group is not None):
                raise ValueError(
                    "For ressource creation, set location or affinity_group" +
                    " not both")
            if location is not None:
                try:
                    self.sms.create_hosted_service(
                        service_name=service_name,
                        label=service_name,
                        location=location)
                    pass
                except Exception, e:
                    raise e
            else:
                try:
                    self.sms.create_hosted_service(
                        service_name=service_name,
                        label=service_name,
                        affinity_group=affinity_group)
                except Exception, e:
                    raise e
        except Exception, e:
            raise e

        # check storage blob
        try:
            self.sms.get_storage_account_properties(storage)
            pass
        except WindowsAzureMissingResourceError:
            # create storage
            foo = self.sms.check_storage_account_name_availability(storage)
            if not foo.result:
                raise ValueError("storage value is unavailable")
            if bool(location is None) != bool(affinity_group is None):
                raise ValueError(
                    "set location or affinity_group, not both for storage")
            if location is not None:
                self.sms.create_storage_account(
                    service_name=storage,
                    description=storage + " made from libcloud",
                    label=storage,
                    location=location,
                    account_type='Standard_LRS')
            else:
                self.sms.create_storage_account(
                    service_name=storage,
                    description=storage + " made from libcloud",
                    label=storage,
                    affinity_group=affinity_group,
                    account_type='Standard_LRS')

        # check configuration from image extra["os"]
        if (image.extra["os"] == u'Linux'):
            vm_conf = LinuxConfigurationSet(
                name,
                vm_user,
                vm_password,
                True)
            network = ConfigurationSet()
            network.configuration_set_type = 'NetworkConfiguration'
            network.input_endpoints.input_endpoints.append(
                ConfigurationSetInputEndpoint('ssh', 'tcp', '22', '22'))
        else:
            vm_conf = WindowsConfigurationSet(
                computer_name=name,
                admin_username=vm_user,
                admin_password=vm_password)
            vm_conf.domain_join = None
            vm_conf.win_rm = None
            network = ConfigurationSet()
            network.configuration_set_type = 'NetworkConfiguration'
            network.input_endpoints.input_endpoints.append(
                ConfigurationSetInputEndpoint('ssh', 'tcp', '3389', '3389'))

        image_name = image.id
        media_link = 'http://%s.blob.core.windows.net/vhds/%s-root-%s.vhd' % (
            storage, name, random.randrange(0, 100, 2))

        os_hd = OSVirtualHardDisk(image_name, media_link)

        # generate random deployement name
        deployment_name = ("deploy-%s-%d") % (
            name, random.randrange(0, 100, 2))

        # go go
        deploiement = self.sms.create_virtual_machine_deployment(
            service_name=service_name,
            deployment_name=deployment_name,
            deployment_slot='production',
            label=name,
            role_name=name,
            system_config=vm_conf,
            os_virtual_hard_disk=os_hd,
            network_config=network,
            role_size=size.id)

        extra = {
            'service_name': service_name,
            'deployment_name': deployment_name,
            'virtual_network_name': virtual_network}

        return Node(
            id=name,
            name=name,
            state=NodeState.PENDING,
            public_ips=[],
            private_ips=[],
            driver=self,
            extra=extra
        )

    def destroy_node(self, node):
        self.sms.delete_deployment(
            service_name=node.extra['service_name'],
            deployment_name=node.extra['deployment_name'])

    def reboot_node(self, node):
        """
            Stop a vm, in StoppedDeallocated mode
        """
        self.sms.restart_role(service_name=node.extra['service_name'],
            deployment_name=node.extra['deployment_name'],
            role_name=node.name)
        return True

    def start_node(self, node):
        """
            Stop a vm, in StoppedDeallocated mode
        """
        self.sms.start_role(service_name=node.extra['service_name'],
            deployment_name=node.extra['deployment_name'],
            role_name=node.name)
        return True

    def list_nodes(self):
        nodes = []
        cloudservices = self.sms.list_hosted_services()

        for i in cloudservices:
            try:
                deploiement = self.sms.get_deployment_by_slot(
                    i.service_name,
                    'production')
                for r in deploiement.role_instance_list:
                    nodes.append(self._to_node(
                        r,
                        virtual_network_name=deploiement.virtual_network_name,
                        service_name=i.service_name,
                        deployment_name=deploiement.name))
            except WindowsAzureMissingResourceError:
                pass

        return nodes

    """ Functions not implemented
    """
    def create_volume_snapshot(self):
        raise NotImplementedError(
            'You cannot create snapshots of '
            'Azure VMs at this time.')

    def attach_volume(self):
        raise NotImplementedError(
            'attach_volume is not supported '
            'at this time.')

    def create_volume(self):
        raise NotImplementedError(
            'create_volume is not supported '
            'at this time.')

    def detach_volume(self):
        raise NotImplementedError(
            'detach_volume is not supported '
            'at this time.')

    def destroy_volume(self):
        raise NotImplementedError(
            'destroy_volume is not supported '
            'at this time.')

    """
    extension ZONE
    ------------------------------------------------------------------------
    """

    def ex_list_storagelocation(self):
        storage = []
        storagecore = self.sms.list_storage_accounts()
        for s in storagecore:
            storage.append(
                self._to_storagelocation(s))
        return storage

    def ex_stop_node(self, node):
        """
            Stop a vm, in StoppedDeallocated mode
        """
        self.sms.shutdown_role(
            service_name=node.extra['service_name'],
            deployment_name=node.extra['deployment_name'],
            role_name=node.name,
            post_shutdown_action="StoppedDeallocated")
        return True

    def ex_get_node_from_name(self, name):
        cloudservices = self.sms.list_hosted_services()

        for i in cloudservices:
            try:
                deploiement = self.sms.get_deployment_by_slot(
                    i.service_name,
                    'production')
                for r in deploiement.role_instance_list:
                    if (r.role_name == name):
                        return self._to_node(
                            r,
                            deploiement.virtual_network_name,
                            service_name=i.service_name,
                            deployment_name=deploiement.name)

            except WindowsAzureMissingResourceError:
                pass
        return None
    """
    Private ZONE
    ------------------------------------------------------------------------
    """

    def _to_node_size(self, data):
        """
        Convert the AZURE_COMPUTE_INSTANCE_TYPES into NodeSize
        """
        return NodeSize(
            id=data.name,
            name=data.label,
            ram=data.memory_in_mb,
            price=0,
            bandwidth=0,
            disk=data.virtual_machine_resource_disk_size_in_mb,
            driver=self,
            extra={
                "cores": data.cores,
                "supported_by_webworkerroles":
                data.supported_by_web_worker_roles,
                "supported_by_virtualmachines":
                data.supported_by_virtual_machines,
                "max_data_disk_count": data.max_data_disk_count,
                "webworker_resource_disk_size_in_mb":
                data.web_worker_resource_disk_size_in_mb
            })

    def _to_image(self, data):
        return NodeImage(
            id=data.name,
            name=data.label,
            driver=self,
            extra={
                'os': data.os,
                'category': data.category,
                'description': data.description,
                'location': data.location,
                'affinity_group': data.affinity_group,
                'media_link': data.media_link
            })

    def _to_location(self, data):
        return NodeLocation(
            id=data.name,
            name=data.display_name,
            country=None,
            driver=self
        )

    def _to_node(self, data, virtual_network_name=u'',
                 service_name=u'', deployment_name=u''):
        public_ip = []
        if data.instance_endpoints is not None:
            if len(data.instance_endpoints) >= 1:
                public_ip = list(set([i.vip for i in data.instance_endpoints]))

        if self.rolesizes is None:
            self.list_sizes()

        size = None
        for i in self.rolesizes:
            if data.instance_size == i.id:
                size = i
        extra = {
            'service_name': service_name,
            'deployment_name': deployment_name}

        if len(virtual_network_name) >= 1:
            extra['virtual_network_name'] = virtual_network_name

        return Node(
            id=data.role_name,
            name=data.role_name,
            state=self.NODE_STATE_MAP.get(
                data.instance_status, NodeState.UNKNOWN),
            size=size,
            driver=self,
            private_ips=[data.ip_address],
            public_ips=public_ip,
            extra=extra
        )

    def _to_virtual_network(self, data):
        return VirtualNetwork(
            id=data.id,
            name=data.name,
            affinity_group=data.affinity_group,
            subnets=data.subnets
        )

    def _to_storagelocation(self, data):
        if (data.storage_service_properties.location == u''):
            location = data.storage_service_properties.affinity_group
        else:
            location = data.storage_service_properties.location

        return StorageLocation(
            id=data.service_name,
            name=data.service_name,
            endpoint=data.storage_service_properties.endpoints[0],
            location=location
        )
    """
    Azure cloud
    ------------------------------------------------------------------------
    """


class StorageLocation(object):
    """
        Represents Azure Virtual storage service
    """

    def __init__(self, id, name, location, endpoint):
        self.id = id
        self.name = name
        self.location = location
        self.endpoint = endpoint

    def __repr__(self):
        return ("Storagelocation %s at %s via %s" %
                (self.name, self.location, self.endpoint))


class VirtualNetwork(object):

    """
    Represents Azure Virtual Network
    """

    def __init__(self, id, name, affinity_group, subnets):
        self.id = id
        self.name = name
        self.affinity_group = affinity_group
        self.subnets = subnets

    def __repr__(self):
        return ('<VirtualNetwork name=%s affinity_group=%s subnets=%s>' %
                (self.name, self.affinity_group, self.subnets))
