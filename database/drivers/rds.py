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
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

# from libcloud.utils.py3 import b, basestring, ensure_string

from libcloud.utils.xml import fixxpath, findtext, findall
# from libcloud.utils.publickey import get_pubkey_ssh2_fingerprint
# from libcloud.utils.publickey import get_pubkey_comment
# from libcloud.utils.iso8601 import parse_date
from libcloud.common.aws import AWSBaseResponse, SignedAWSConnection
from libcloud.common.aws import DEFAULT_SIGNATURE_VERSION
from libcloud.common.types import (InvalidCredsError, MalformedResponseError,
                                   LibcloudError)
# from libcloud.database.providers import Provider
from libcloud.database.base import DatabaseNodeDriver
from libcloud.database.base import DBInstance, DBEngine
from libcloud.compute.drivers.ec2 import EC2NetworkSubnet
# from libcloud.database.base import KeyPair
# from libcloud.database.types import NodeState, KeyPairDoesNotExistError, \
#     StorageVolumeState


__all__ = [
]

API_VERSION = '2014-10-31'
NAMESPACE = 'http://rds.amazonaws.com/doc/%s/' % (API_VERSION)


REGION_DETAILS = {
    # US East (Northern Virginia) Region
    'us-east-1': {
        'endpoint': 'rds.us-east-1.amazonaws.com',
        'api_name': 'rds_us_east',
        'country': 'USA',
        'signature_version': '2',
    },
    # US West (Northern California) Region
    'us-west-1': {
        'endpoint': 'rds.us-west-1.amazonaws.com',
        'api_name': 'rds_us_west',
        'country': 'USA',
        'signature_version': '2',
    },
    # US West (Oregon) Region
    'us-west-2': {
        'endpoint': 'rds.us-west-2.amazonaws.com',
        'api_name': 'rds_us_west_oregon',
        'country': 'USA',
        'signature_version': '2',
    },
    # EU (Ireland) Region
    'eu-west-1': {
        'endpoint': 'rds.eu-west-1.amazonaws.com',
        'api_name': 'rds_eu_west',
        'country': 'Ireland',
        'signature_version': '2',
    },
    # Asia Pacific (Singapore) Region
    'ap-southeast-1': {
        'endpoint': 'rds.ap-southeast-1.amazonaws.com',
        'api_name': 'rds_ap_southeast',
        'country': 'Singapore',
        'signature_version': '2',
    },
    # Asia Pacific (Tokyo) Region
    'ap-northeast-1': {
        'endpoint': 'rds.ap-northeast-1.amazonaws.com',
        'api_name': 'rds_ap_northeast',
        'country': 'Japan',
        'signature_version': '2',
    },
    # South America (Sao Paulo) Region
    'sa-east-1': {
        'endpoint': 'rds.sa-east-1.amazonaws.com',
        'api_name': 'rds_sa_east',
        'country': 'Brazil',
        'signature_version': '2',
    },
    # EU (Germany) Region
    'eu-central-1': {
        'endpoint': 'rds.eu-central-1.amazonaws.com',
        'api_name': 'rds_eu-central',
        'country': 'Germany',
        'signature_version': '2',
    },
}

VALID_RDS_REGIONS = REGION_DETAILS.keys()


class RDSResponse(AWSBaseResponse):

    """
    RDS specific response parsing and error handling.
    """

    def parse_error(self):
        # err_list = []
        # Okay, so for Eucalyptus, you can get a 403, with no body,
        # if you are using the wrong user/password.
        msg = "Failure: 403 Forbidden"
        if self.status == 403 and self.body[:len(msg)] == msg:
            raise InvalidCredsError(msg)

        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError("Failed to parse XML",
                                         body=self.body, driver=RDSNodeDriver)

        s = ""
        # for e in body:
        #     l = e.getchildren()
        #     for i in l:
        #         s = s + i.text

        for el in body.findall(fixxpath(xpath='Error',
                                        namespace=NAMESPACE)):
            inner = el.getchildren()
            for i in inner:
                s = s + " : " + i.text
            s = s + "\n"

        if s == "":
            for el in body.findall(fixxpath(xpath='Error',
                                            namespace="http://webservices.amazon.com/AWSFault/2005-15-09")):
                inner = el.getchildren()
                for i in inner:
                    s = s + " : " + i.text
                s = s + "\n"

        raise LibcloudError(s, self.status)


class IdempotentParamError(LibcloudError):

    """
    Request used the same client token as a previous,
    but non-identical request.
    """

    def __str__(self):
        return repr(self.value)


class RDSConnection(SignedAWSConnection):

    """
    Represents a single connection to the EC2 Endpoint.
    """

    version = API_VERSION
    host = REGION_DETAILS['us-east-1']['endpoint']
    responseCls = RDSResponse
    service_name = 'rds'


class RDSNodeDriver(DatabaseNodeDriver):

    """
    Amazon RDS node driver.
    """

    connectionCls = RDSConnection
    name = 'Amazon RDS'
    website = 'http://aws.amazon.com/rds/'
    path = '/'

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 region='us-east-1', **kwargs):
        if hasattr(self, '_region'):
            region = self._region

        if region not in VALID_RDS_REGIONS:
            raise ValueError('Invalid region: %s' % (region))

        details = REGION_DETAILS[region]
        self.region_name = region
        self.api_name = details['api_name']
        self.country = details['country']
        self.signature_version = details.pop('signature_version',
                                             DEFAULT_SIGNATURE_VERSION)

        host = host or details['endpoint']

        super(RDSNodeDriver, self).__init__(key=key, secret=secret,
                                            secure=secure, host=host,
                                            port=port, **kwargs)

    def list_acc_atts(self):
        """
        Lists all of the attributes for a customer account
        """

        params = {'Action': 'DescribeAccountAttributes'}

        elem = self.connection.request(self.path, params=params).object

        return elem

    def list_db_instances(self):
        params = {'Action': 'DescribeDBInstances'}

        elem = self.connection.request(self.path, params=params).object

        # for el in elem.findall(fixxpath(xpath='DescribeDBInstancesResult/DBInstances/DBInstance',
        #                                 namespace=NAMESPACE)):
        #     e = findtext(element=el,
        #                  xpath='BackupRetentionPeriod',
        #                  namespace=NAMESPACE)
        #     print e

        return self.to_db_instances(elem)

    def to_db_instances(self, response):
        return [self.to_db_instance(el) for el in response.findall(
            fixxpath(xpath='DescribeDBInstancesResult/DBInstances/DBInstance',
                     namespace=NAMESPACE))]

    def to_db_instance(self, element):

        name = findtext(element=element,
                        xpath='DBName',
                        namespace=NAMESPACE)

        id = findtext(element=element,
                      xpath='DBInstanceIdentifier',
                      namespace=NAMESPACE)

        status = findtext(element=element,
                      xpath='DBInstanceStatus',
                      namespace=NAMESPACE)

        # <Engine>mysql</Engine>
        engine = findtext(element=element,
                          xpath='Engine',
                          namespace=NAMESPACE)

        # <EngineVersion>5.6.13</EngineVersion>
        enginev = findtext(element=element,
                          xpath='EngineVersion',
                          namespace=NAMESPACE)

        # <InstanceCreateTime>2014-01-29T22:58:24.231Z</InstanceCreateTime>
        creationdate = findtext(element=element,
                          xpath='InstanceCreateTime',
                          namespace=NAMESPACE)

        # <AllocatedStorage>5</AllocatedStorage>
        allocated = findtext(element=element,
                             xpath='AllocatedStorage',
                             namespace=NAMESPACE)

        # <DBInstanceClass>db.t1.micro</DBInstanceClass>
        size = findtext(element=element,
                        xpath='DBInstanceClass',
                        namespace=NAMESPACE)

        # <MasterUsername>myawsuser</MasterUsername>
        user = findtext(element=element,
                        xpath='MasterUsername',
                        namespace=NAMESPACE)

        # <AvailabilityZone>us-west-2b</AvailabilityZone>
        availabzone = findtext(element=element,
                      xpath='AvailabilityZone',
                      namespace=NAMESPACE)

        # <BackupRetentionPeriod>7</BackupRetentionPeriod>
        backupretention = findtext(element=element,
                      xpath='BackupRetentionPeriod',
                      namespace=NAMESPACE)

        # <PreferredMaintenanceWindow>sun:06:13-sun:06:43</PreferredMaintenanceWindow>
        maintenancewindow = findtext(
                      element=element,
                      xpath='PreferredMaintenanceWindow',
                      namespace=NAMESPACE)

        #<PreferredBackupWindow>10:07-10:37</PreferredBackupWindow>
        backupwindow = findtext(
                      element=element,
                      xpath='PreferredBackupWindow',
                      namespace=NAMESPACE)

        # <LatestRestorableTime>2014-04-21T17:15:00Z</LatestRestorableTime
        latestrestore = findtext(
                      element=element,
                      xpath='LatestRestorableTime',
                      namespace=NAMESPACE)

        # <PubliclyAccessible>true</PubliclyAccessible>
        public = findtext(
                      element=element,
                      xpath='PubliclyAccessible',
                      namespace=NAMESPACE)

        # <LicenseModel>general-public-license</LicenseModel>
        license = findtext(
                      element=element,
                      xpath='LicenseModel',
                      namespace=NAMESPACE)

        # <MultiAZ>false</MultiAZ>
        multiaz = findtext(
                      element=element,
                      xpath='MultiAZ',
                      namespace=NAMESPACE)

        vpcsgs = element.find(
            fixxpath(xpath='VpcSecurityGroups',
                     namespace=NAMESPACE))

        lvpcsg = []
        for vpcsg in vpcsgs.getchildren():
            d = {"name": findtext(element=vpcsg,
                                       xpath='VpcSecurityGroupId',
                                       namespace=NAMESPACE),
                 "status": findtext(element=vpcsg,
                                    xpath='Status',
                                    namespace=NAMESPACE)
                 }
            lvpcsg.append(d)

        # <DBParameterGroups>
        #   <DBParameterGroup>
        #     <ParameterApplyStatus>in-sync</ParameterApplyStatus>
        #     <DBParameterGroupName>default.mysql5.6</DBParameterGroupName>
        #   </DBParameterGroup>
        # </DBParameterGroups>

        paramgrps = element.find(
            fixxpath(xpath='DBParameterGroups',
                     namespace=NAMESPACE))

        lpg = []
        for pg in paramgrps.getchildren():
            # print pg.getchildren()
            d = {"name": findtext(element=pg,
                                       xpath='DBParameterGroupName',
                                       namespace=NAMESPACE),
                 "status": findtext(
                                    element=pg,
                                    xpath='ParameterApplyStatus',
                                    namespace=NAMESPACE)
                 }
            lpg.append(d)

        # <Endpoint>
        #   <Port>3306</Port>
        #   <Address>mysqlexampledb.c6c1rntzufv0.us-west-2.rds.amazonaws.com</Address>
        # </Endpoint>

        ept = element.find(fixxpath(xpath='Endpoint',
                                    namespace=NAMESPACE))
        if ept is None:
            endpoint = {}
        else:
            endpoint = {"port": findtext(element=ept,
                                         xpath='Port',
                                         namespace=NAMESPACE),
                        "address": findtext(element=ept,
                                            xpath='Address',
                                            namespace=NAMESPACE)}

        # <OptionGroupMemberships>
        #   <OptionGroupMembership>
        #     <OptionGroupName>default:mysql-5-6</OptionGroupName>
        #     <Status>in-sync</Status>
        #   </OptionGroupMembership>
        # </OptionGroupMemberships>

        optgps = element.find(fixxpath(xpath='OptionGroupMemberships',
                                       namespace=NAMESPACE))

        loption = []
        for grp in optgps.getchildren():
            d = {"name": findtext(element=grp,
                                  xpath='OptionGroupName',
                                  namespace=NAMESPACE),
                 "status": findtext(element=grp,
                                    xpath='Status',
                                    namespace=NAMESPACE)
                 }
            loption.append(d)


        # <DBSecurityGroups>
        #   <DBSecurityGroup>
        #     <Status>active</Status>
        #     <DBSecurityGroupName>my-db-secgroup</DBSecurityGroupName>
        #   </DBSecurityGroup>
        # </DBSecurityGroups>

        secgps = element.find(fixxpath(xpath='DBSecurityGroups',
                                       namespace=NAMESPACE))

        lsecg = []
        for secgrp in secgps.getchildren():
            d = {"name": findtext(element=secgrp,
                                  xpath='DBSecurityGroupName',
                                  namespace=NAMESPACE),
                 "status": findtext(element=secgrp,
                                    xpath='Status',
                                    namespace=NAMESPACE)
                 }
            lsecg.append(d)

        # <ReadReplicaDBInstanceIdentifiers/>
        readrepdbids = element.find(fixxpath(
            xpath='ReadReplicaDBInstanceIdentifiers',
            namespace=NAMESPACE))

        for readrepdbid in readrepdbids.getchildren():
            print readrepdbid

        # <PendingModifiedValues/>
        pendingmodifs = element.find(fixxpath(
            xpath='PendingModifiedValues',
            namespace=NAMESPACE))

        pmvlist = []
        for pendingmodif in pendingmodifs.getchildren():
            pmvlist.append(
                {
                    pendingmodif.tag.replace("{"+NAMESPACE+"}", "") : pendingmodif.text
                })

        extra = {"backup_retention": backupretention,
                 "maintenance_window": maintenancewindow,
                 "backup_window": backupwindow,
                 "latest_restore": latestrestore,
                 "public": public,
                 "license": license,
                 "multi_az": multiaz,
                 "pending_modified_values": pmvlist,
                 "security groups": lsecg,
                 "option_groups": loption,
                 "endpoint": endpoint,
                 "parameter_groups": lpg,
                 "vpc_security_groups": lvpcsg
                 }

        return DBInstance(name=name, id=id, status=status, engine=engine,
                          engine_version=enginev, creation_date=creationdate,
                          allocated=allocated, size=size, user=user,
                          location=availabzone,  driver=RDSNodeDriver,
                          extra=extra)

    def list_db_engines(self):
        params = {'Action': 'DescribeDBEngineVersions'}

        elem = self.connection.request(self.path, params=params).object
        return self.to_db_engines(elem)

    def to_db_engines(self, response):
        return [self.to_db_engine(el) for el in response.findall(
            fixxpath(
                xpath='DescribeDBEngineVersionsResult/DBEngineVersions/'
                      'DBEngineVersion',
                namespace=NAMESPACE))]

    def to_db_engine(self, element):
        # <Engine>mysql</Engine>
        DbMS = findtext(element=element,
                        xpath='Engine',
                        namespace=NAMESPACE)

        # <DBParameterGroupFamily>mysql5.1</DBParameterGroupFamily>
        family = findtext(element=element,
                          xpath='DBParameterGroupFamily',
                          namespace=NAMESPACE)

        # <DBEngineDescription>MySQL Community Edition</DBEngineDescription>
        description = findtext(element=element,
                               xpath='DBEngineDescription',
                               namespace=NAMESPACE)

        # <EngineVersion>5.1.57</EngineVersion>
        version = findtext(element=element,
                           xpath='EngineVersion',
                           namespace=NAMESPACE)

        # <DBEngineVersionDescription>MySQL 5.1.57</DBEngineVersionDescription>
        version_description = findtext(element=element,
                                       xpath='DBEngineVersionDescription',
                                       namespace=NAMESPACE)

        return DBEngine(dbms=DbMS, family=family, version=version,
                        driver=RDSNodeDriver, description=description,
                        version_description=version_description)

    def create_db_instance(self, instance_class, id, engine,
                           root_log, root_pwd, allocated, **kwargs):
        """
            instance_class, id, engine,
                           root_log, root_pwd, allocated,
             auto_minorv_upgrade
             retention
             cluster_id
             name
             param_group
             security_groups list of Object Ec2
             subnet Object Ec2
             engine_version major or minor
             iops
            option_group Object
            port
            backup_window  hh24:mi-hh24:mi UTC
            maintenance_window ddd:hh24:mi-ddd:hh24:mi UTC  Mon, Tue, Wed, Thu, Fri, Sat, Sun


        """

        params = {
            'Action': 'CreateDBInstance',
            'DBInstanceClass': instance_class,
            'DBInstanceIdentifier': id,
            'Engine': engine,
            'MasterUsername': root_log,
            'MasterUserPassword': root_pwd,
            'AllocatedStorage': allocated,
        }

        if 'auto_minorv_upgrade' in kwargs:
            if kwargs["auto_minorv_upgrade"]:
                params["AutoMinorVersionUpgrade"] = "true"
            else:
                params["AutoMinorVersionUpgrade"] = "false"

        if 'bckpretention' in kwargs:
            if kwargs["bckpretention"] is not None:
                params["BackupRetentionPeriod"] = kwargs["bckpretention"]

        if "cluster_id" in kwargs:
            if kwargs["cluster_id"] is not None:
                params["DBClusterIdentifier"] = kwargs["cluster_id"]

        if "name" in kwargs:
            if kwargs["name"] is not None:
                params["DBName"] = kwargs["name"]

        if "param_group" in kwargs:
            if kwargs["param_group"] is not None:
                params["DBParameterGroupName"] = kwargs["param_group"]

        if "security_groups" in kwargs:
            if kwargs["security_groups"] is not None:
                for sig in range(len(kwargs["security_groups"])):
                    params['VpcSecurityGroupIds.member.%d' % (sig + 1,)] =\
                        kwargs["security_groups"][sig]

        if "subnet_group" in kwargs:
            if kwargs["subnet_group"] is not None:
                params["DBSubnetGroupName"] = kwargs["subnet_group"].name

        if "engine_version" in kwargs:
            if kwargs["engine_version"] is not None:
                params["EngineVersion"] = kwargs["engine_version"]

        if "iops" in kwargs:
            if kwargs["iops"] is not None:
                params["Iops"] = kwargs["iops"]

        if "option_group" in kwargs:
            if kwargs["option_group"] is not None:
                params["OptionGroupName"] = kwargs["option_group"].name

        if "port" in kwargs:
            if kwargs["port"] is not None:
                params["Port"] = kwargs["port"].name

        if "backup_window" in kwargs:
            if kwargs["backup_window"] is not None:
                params["PreferredBackupWindow"] = kwargs["backup_window"]

        if "maintenance_window" in kwargs:
            if kwargs["maintenance_window"] is not None:
                params["PreferredMaintenanceWindow"] = kwargs[
                                                    "maintenance_window"]

        if "public" in kwargs:
            if kwargs["public"]:
                params["PubliclyAccessible"] = "true"
            else:
                params["PubliclyAccessible"] = "false"

        if "encypt_storage" in kwargs:
            if kwargs["encypt_storage"]:
                params["StorageEncrypted"] = "true"
            else:
                params["StorageEncrypted"] = "false"

        if "storage_type" in kwargs:
            if kwargs["storage_type"] is not None:
                params["StorageType"] = kwargs[
                                                    "storage_type"]

        if "iops" in kwargs:
            if kwargs["iops"] is not None:
                params["Iops"] = kwargs["iops"]

        if "tags" in kwargs:
            if kwargs["tags"] is not None:
                i = 0
                for k, v in kwargs["tags"].items():
                    params['Tags.member.%d.Key' % (i + 1,)] =\
                        k
                    params['Tags.member.%d.Value' % (i + 1,)] =\
                        v
                    i += 1

        object = self.connection.request(self.path, params=params).object

        l = object.find(fixxpath(
                xpath='CreateDBInstanceResult/DBInstance',
                namespace=NAMESPACE))
        return self.to_db_instance(l)

    def delete_db_instance(self, id, skip_snapshot=True,
                           snapshot_id=None):
        params = {
            'Action': 'DeleteDBInstance',
            'DBInstanceIdentifier': id,
        }
        if not skip_snapshot:
            params["FinalDBSnapshotIdentifier"] = snapshot_id
        else:
            params["SkipFinalSnapshot"] = "true"

        object = self.connection.request(self.path, params=params).object
        l = object.find(fixxpath(
                xpath='DeleteDBInstanceResult/DBInstance',
                namespace=NAMESPACE))
        return self.to_db_instance(l)

        # .find(fixxpath(
        #         xpath='DescribeDBEngineVersionsResult/DBEngineVersions/'
        #               'DBEngineVersion',
        #         namespace=NAMESPACE))

    def list_db_subnet_groups(self):
        params = {
            'Action': 'DescribeDBSubnetGroups'
        }
        res = self.connection.request(self.path, params=params)
        object = res.object
        res = self.to_db_subnet_groups(object)
        return res

    def to_db_subnet_groups(self, response):
        return [self.to_db_subnet_group(el) for el in response.findall(
            fixxpath(
                xpath='DescribeDBSubnetGroupsResult/DBSubnetGroups/'
                      'DBSubnetGroup',
                namespace=NAMESPACE))]

    def to_db_subnet_group(self, element):

        # <VpcId>vpc-e7abbdce</VpcId>
        vpcID = findtext(element=element,
                         xpath='VpcId',
                         namespace=NAMESPACE)

        # <SubnetGroupStatus>Complete</SubnetGroupStatus>
        status = findtext(element=element,
                          xpath='SubnetGroupStatus',
                          namespace=NAMESPACE)

        # <DBSubnetGroupDescription>DB subnet group 1</DBSubnetGroupDescription>
        description = findtext(element=element,
                               xpath='DBSubnetGroupDescription',
                               namespace=NAMESPACE)

        # <DBSubnetGroupName>mydbsubnetgroup1</DBSubnetGroupName>
        name = findtext(element=element,
                        xpath='DBSubnetGroupName',
                        namespace=NAMESPACE)
        # <Subnets>
        #   <Subnet>
        #     <SubnetStatus>Active</SubnetStatus>
        #     <SubnetIdentifier>subnet-e8b3e5b1</SubnetIdentifier>
        #     <SubnetAvailabilityZone>
        #       <Name>us-west-2a</Name>
        #       <ProvisionedIopsCapable>false</ProvisionedIopsCapable>
        #     </SubnetAvailabilityZone>
        #   </Subnet>
        #   <Subnet>
        #     <SubnetStatus>Active</SubnetStatus>
        #     <SubnetIdentifier>subnet-44b2f22e</SubnetIdentifier>
        #     <SubnetAvailabilityZone>
        #       <Name>us-west-2b</Name>
        #       <ProvisionedIopsCapable>false</ProvisionedIopsCapable>
        #     </SubnetAvailabilityZone>
        #   </Subnet>
        # </Subnets>

        subnets = element.find(fixxpath(xpath='Subnets',
                                        namespace=NAMESPACE))

        lsubs = []
        for sub in subnets.getchildren():
            subnet_id = findtext(element=sub,
                                 xpath='SubnetIdentifier',
                                 namespace=NAMESPACE)
            subname = ""
            state = findtext(element=sub,
                             xpath='SubnetStatus',
                             namespace=NAMESPACE)
            zone = findtext(element=sub,
                            xpath='SubnetAvailabilityZone/Name',
                            namespace=NAMESPACE)
            extrasub = {}
            extrasub["zone"] = zone
            subobject = EC2NetworkSubnet(subnet_id, subname, state, extrasub)

            lsubs.append(subobject)

        extra = {}
        extra["description"] = description
        extra["subnets"] = lsubs

        return RDSSubnetGroup(name=name, vpcid=vpcID, state=status,
                              driver=RDSNodeDriver, extra=extra)

    def create_db_subnet_group(self, name, subnet_id_list, description=""):
        """


        """

        params = {
            'Action': 'CreateDBSubnetGroup',
            'DBSubnetGroupDescription': description,
            'DBSubnetGroupName': name
        }
        if subnet_id_list:
            if not isinstance(subnet_id_list, (tuple, list)):
                subnet_id_list = [subnet_id_list]

            for sig in range(len(subnet_id_list)):
                params['SubnetIds.member.%d' % (sig + 1,)] =\
                    subnet_id_list[sig]
        print params
        object = self.connection.request(self.path, params=params).object

        l = object.find(fixxpath(
                xpath='CreateDBSubnetGroupResult/DBSubnetGroup',
                namespace=NAMESPACE))
        return self.to_db_subnet_group(l)

    def delete_db_subnet_group(self, id):
        """
            TODO

        """

    def list_db_security_groups(self):
        """
            TODO

        """
        params = {'Action': 'DescribeDBSecurityGroups'}

        elem = self.connection.request(self.path, params=params).object
        return self._to_db_security_groups(elem)

    def _to_db_security_groups(self, response):
        """
            TODO

        """
        return [self._to_db_security_group(el) for el in response.findall(
            fixxpath(
                xpath='DescribeDBSecurityGroupsResult/DBSecurityGroups/'
                      'DBSecurityGroup',
                namespace=NAMESPACE))]

    def _to_db_security_group(self, element):
        # <Engine>mysql</Engine>

        # <DBSecurityGroupDescription>My security group</DBSecurityGroupDescription>
        description = findtext(element=element,
                               xpath='DBSecurityGroupDescription',
                               namespace=NAMESPACE)

        # <DBSecurityGroupName>my-secgrp</DBSecurityGroupName>
        name = findtext(element=element,
                        xpath='DBSecurityGroupName',
                        namespace=NAMESPACE)

        owner_id = findtext(element=element,
                            xpath='OwnerId',
                            namespace=NAMESPACE)

        ipranges = element.find(fixxpath(xpath='IPRanges',
                                         namespace=NAMESPACE))

        lips = []
        for iprange_obj in ipranges.getchildren():
            iprange = findtext(element=iprange_obj,
                               xpath='CIDRIP',
                               namespace=NAMESPACE)
            ipstate = findtext(element=iprange_obj,
                               xpath='Status',
                               namespace=NAMESPACE)
            ip_obj = {"cidr": iprange,
                      "status": ipstate}

            lips.append(ip_obj)

        # EC2SecurityGroups

        ec2_sgs = element.find(fixxpath(xpath='EC2SecurityGroups',
                                        namespace=NAMESPACE))

        l_ec2_sec_gr = []
        for ec2_sg_obj in ec2_sgs.getchildren():
            ec2_sg_name = findtext(element=ec2_sg_obj,
                                   xpath='EC2SecurityGroupName',
                                   namespace=NAMESPACE)

            ec2_sg_owner = findtext(element=ec2_sg_obj,
                                    xpath='EC2SecurityGroupOwnerId',
                                    namespace=NAMESPACE)

            ec2_sg_id = findtext(element=ec2_sg_obj,
                                 xpath='EC2SecurityGroupId',
                                 namespace=NAMESPACE)

            ec2_sg_status = findtext(element=ec2_sg_obj,
                                     xpath='Status',
                                     namespace=NAMESPACE)

            ec2sg_obj = {"name": ec2_sg_name,
                         "id": ec2_sg_id,
                         "owner_id": ec2_sg_owner,
                         "status": ec2_sg_status}

            l_ec2_sec_gr.append(ec2sg_obj)

        extra = {}
        extra["EC2_Security_Groups"] = l_ec2_sec_gr
        extra["ip_ranges"] = lips
        extra["owner_id"] = owner_id

        return RDSSecurityGroup(name=name, description=description,
                                driver=RDSNodeDriver, extra=extra)

    def create_db_security_group(self, name, description):
        """
            TODO

        """
        params = {
            'Action': 'CreateDBSecurityGroup',
            'DBSecurityGroupDescription': description,
            'DBSecurityGroupName': name
        }

        object = self.connection.request(self.path, params=params).object

        l = object.find(fixxpath(
                xpath='CreateDBSecurityGroupResult/DBSecurityGroup',
                namespace=NAMESPACE))
        return self._to_db_security_group(l)

    def delete_db_security_group(self, groupname):
        """
            TODO

        """
        params = {
            'Action': 'DeleteDBSecurityGroup',
            'DBSecurityGroupName': groupname,
        }

        object = self.connection.request(self.path, params=params).object
        l = object.find(fixxpath(
                xpath='ResponseMetadata',
                namespace=NAMESPACE))
        return (len(l) > 0)

    def allow_cidr_in_db_security_group(self, id, cidr):
        """
            TODO

        """

    def revoke_cidr_in_db_security_group(self, id, cidr):
        """
            TODO

        """

    def list_db_snapshots(self):
        params = {
            'Action': 'DescribeDBSnapshots'
        }
        elem = self.connection.request(self.path, params=params).object
        return self._to_db_snapshots(elem)

    def _to_db_snapshots(self, response):
        """
            TODO

        """
        return [self._to_db_snapshot(el) for el in response.findall(
            fixxpath(
                xpath='DescribeDBSnapshotsResult/DBSnapshots/'
                      'DBSnapshot',
                namespace=NAMESPACE))]

    def _to_db_snapshot(self, element):
        # <Port>3306</Port>
        port = findtext(element=element,
                        xpath='Port',
                        namespace=NAMESPACE)

        # <OptionGroupName>default:mysql-5-6</OptionGroupName>
        option_group = findtext(element=element,
                                xpath='OptionGroupName',
                                namespace=NAMESPACE)

        # <Engine>mysql</Engine>
        engine = findtext(element=element,
                          xpath='Engine',
                          namespace=NAMESPACE)

        # <Status>available</Status>
        state = findtext(element=element,
                         xpath='Status',
                         namespace=NAMESPACE)

        # <SnapshotType>manual</SnapshotType>
        type = findtext(element=element,
                        xpath='SnapshotType',
                        namespace=NAMESPACE)

        # <LicenseModel>general-public-license</LicenseModel>
        license = findtext(element=element,
                           xpath='SnapshotType',
                           namespace=NAMESPACE)

        # <EngineVersion>5.6.13</EngineVersion>
        enginev = findtext(element=element,
                           xpath='EngineVersion',
                           namespace=NAMESPACE)

        # <DBInstanceIdentifier>my-mysqlexampledb</DBInstanceIdentifier>
        db_instance_id = findtext(element=element,
                                  xpath='DBInstanceIdentifier',
                                  namespace=NAMESPACE)

        # <DBSnapshotIdentifier>my-test-restore-snapshot</DBSnapshotIdentifier>
        id = findtext(element=element,
                      xpath='DBSnapshotIdentifier',
                      namespace=NAMESPACE)

        # <SnapshotCreateTime>2014-03-28T19:57:16.707Z</SnapshotCreateTime>
        creationdate = findtext(element=element,
                                xpath='SnapshotCreateTime',
                                namespace=NAMESPACE)

        # <AvailabilityZone>us-west-2b</AvailabilityZone>
        az = findtext(element=element,
                      xpath='AvailabilityZone',
                      namespace=NAMESPACE)

        # <InstanceCreateTime>2014-01-29T22:58:24.231Z</InstanceCreateTime>
        instance_creation_date = findtext(element=element,
                                          xpath='InstanceCreateTime',
                                          namespace=NAMESPACE)

        # <PercentProgress>100</PercentProgress>
        progress = findtext(element=element,
                            xpath='PercentProgress',
                            namespace=NAMESPACE)

        # <AllocatedStorage>5</AllocatedStorage>
        allocated = findtext(element=element,
                             xpath='AllocatedStorage',
                             namespace=NAMESPACE)

        # <MasterUsername>awsmyuser</MasterUsername>
        master_user = findtext(element=element,
                               xpath='MasterUsername',
                               namespace=NAMESPACE)

        extra = {
            "port": port,
            "option_group": option_group,
            "engine": engine,
            "license": license,
            "engine_version": enginev,
            "availability_zone": az,
            "db_instance_creation_date": instance_creation_date,
            "progression": progress,
            "master_user_name": master_user,
            "type": type,
        }

        return RDSSnapshot(id=id, db_id=db_instance_id, state=state,
                           allocated=allocated, creationdate=creationdate,
                           driver=RDSNodeDriver, extra=extra)

    def delete_db_snapshot(self, snapshot_id):
        params = {
            'Action': 'DeleteDBSnapshot',
            'DBSnapshotIdentifier': snapshot_id
        }
        object = self.connection.request(self.path, params=params).object
        l = object.find(fixxpath(
                xpath='DeleteDBSnapshotResult/DBSnapshot',
                namespace=NAMESPACE))
        return self._to_db_snapshot(l)

    def take_snapshot(self, snapshot_identifier, db_instance_id):
        params = {
            'Action': 'CreateDBSnapshot',
            'DBInstanceIdentifier': db_instance_id,
            'DBSnapshotIdentifier': snapshot_identifier
        }

        object = self.connection.request(self.path, params=params).object

        l = object.find(fixxpath(
                xpath='CreateDBSnapshotResult/DBSnapshot',
                namespace=NAMESPACE))
        return self._to_db_snapshot(l)

    def get_db_snapshots_for_db(self, db_instance):
        params = {
            'Action': 'DescribeDBSnapshots',
            'DBInstanceIdentifier': db_instance.id
        }
        elem = self.connection.request(self.path, params=params).object
        return self._to_db_snapshots(elem)

    def get_db_snapshot(self, db_snapshot_id):
        params = {
            'Action': 'DescribeDBSnapshots',
            'DBSnapshotIdentifier': db_snapshot_id
        }
        object = self.connection.request(self.path, params=params).object
        l = object.find(fixxpath(
                xpath='DescribeDBSnapshotsResult/DBSnapshots/DBSnapshot',
                namespace=NAMESPACE))
        return self._to_db_snapshot(l)

    def restore_db_instance_from_db_snapshot(self, instance_class, id,
                                             snapshot_id, **kwargs):
        """
            instance_class, id, engine,
                           root_log, root_pwd, allocated,
             auto_minorv_upgrade
             retention
             cluster_id
             name
             param_group
             security_groups list of Object Ec2
             subnet Object Ec2
             engine_version major or minor
             iops
            option_group Object
            port
            backup_window  hh24:mi-hh24:mi UTC
            maintenance_window ddd:hh24:mi-ddd:hh24:mi UTC  Mon, Tue, Wed, Thu, Fri, Sat, Sun


        """

        params = {
            'Action': 'RestoreDBInstanceFromDBSnapshot',
            'DBInstanceClass': instance_class,
            'DBInstanceIdentifier': id,
            'DBSnapshotIdentifier': snapshot_id,
        }

        if 'engine' in kwargs:
            if kwargs["engine"] is not None:
                params["Engine"] = kwargs["engine"]

        if 'auto_minorv_upgrade' in kwargs:
            if kwargs["auto_minorv_upgrade"]:
                params["AutoMinorVersionUpgrade"] = "true"
            else:
                params["AutoMinorVersionUpgrade"] = "false"

        if "name" in kwargs:
            if kwargs["name"] is not None:
                params["DBName"] = kwargs["name"]

        if "subnet_group" in kwargs:
            if kwargs["subnet_group"] is not None:
                params["DBSubnetGroupName"] = kwargs["subnet_group"].name

        if "engine_version" in kwargs:
            if kwargs["engine_version"] is not None:
                params["EngineVersion"] = kwargs["engine_version"]

        if "iops" in kwargs:
            if kwargs["iops"] is not None:
                params["Iops"] = kwargs["iops"]

        if "option_group" in kwargs:
            if kwargs["option_group"] is not None:
                params["OptionGroupName"] = kwargs["option_group"].name

        if "port" in kwargs:
            if kwargs["port"] is not None:
                params["Port"] = kwargs["port"]

        if "public" in kwargs:
            if kwargs["public"]:
                params["PubliclyAccessible"] = "true"
            else:
                params["PubliclyAccessible"] = "false"

        if "storage_type" in kwargs:
            if kwargs["storage_type"] is not None:
                params["StorageType"] = kwargs[
                                                    "storage_type"]

        if "iops" in kwargs:
            if kwargs["iops"] is not None:
                params["Iops"] = kwargs["iops"]

        if "copy_tags" in kwargs:
            if kwargs["public"]:
                params["CopyTagsToSnapshot"] = "true"
            else:
                params["CopyTagsToSnapshot"] = "false"

        if "tags" in kwargs:
            if kwargs["tags"] is not None:
                i = 0
                for k, v in kwargs["tags"].items():
                    params['Tags.member.%d.Key' % (i + 1,)] =\
                        k
                    params['Tags.member.%d.Value' % (i + 1,)] =\
                        v
                    i += 1

        object = self.connection.request(self.path, params=params).object

        l = object.find(fixxpath(
                xpath='RestoreDBInstanceFromDBSnapshotResult/DBInstance',
                namespace=NAMESPACE))
        return self.to_db_instance(l)

    def modify_db_instance(self, db_id, apply_now, **kwargs):
        params = {
            'Action': 'ModifyDBInstance',
            'DBInstanceIdentifier': db_id
         }

        if apply_now is not None:
            if apply_now:
                params["ApplyImmediately"] = "true"
            else:
                params["ApplyImmediately"] = "false"

        if "storage_size" in kwargs:
            if kwargs["storage_size"] is not None:
                params["AllocatedStorage"] = kwargs["storage_size"]

        if "maintenance_window" in kwargs:
            if kwargs["maintenance_window"] is not None:
                params["PreferredMaintenanceWindow"] = kwargs[
                                                    "maintenance_window"]

        if "storage_type" in kwargs:
            if kwargs["storage_type"] is not None:
                params["StorageType"] = kwargs["storage_type"]

        if "backup_window" in kwargs:
            if kwargs["backup_window"] is not None:
                params["PreferredBackupWindow"] = kwargs["backup_window"]

        if "multi_az" in kwargs:
            if kwargs["multi_az"] is not None:
                params["MultiAZ"] = kwargs["multi_az"]

        if "master_user_pass" in kwargs:
            if kwargs["master_user_pass"] is not None:
                params["MasterUserPassword"] = kwargs["master_user_pass"]

        if "iops" in kwargs:
            if kwargs["iops"] is not None:
                params["Iops"] = kwargs["iops"]

        if "enginev" in kwargs:
            if kwargs["enginev"] is not None:
                params["EngineVersion"] = kwargs["enginev"]

        if "domain" in kwargs:
            if kwargs["domain"] is not None:
                params["Domain"] = kwargs["domain"]

        if "instance_class" in kwargs:
            if kwargs["instance_class"] is not None:
                params["DBInstanceClass"] = kwargs["instance_class"]

        if "backup_retention" in kwargs:
            if kwargs["backup_retention"] is not None:
                params["BackupRetentionPeriod"] = kwargs[
                                                "backup_retention"]

        if "allow_major_upgrade" in kwargs:
            if kwargs["allow_major_upgrade"] is not None:
                if kwargs["allow_major_upgrade"]:
                    params["AllowMajorVersionUpgrade"] = "true"
                else:
                    params["AllowMajorVersionUpgrade"] = "false"

        if "minor_upgrade" in kwargs:
            if kwargs["minor_upgrade"] is not None:
                if kwargs["minor_upgrade"]:
                    params["AutoMinorVersionUpgrade"] = "true"
                else:
                    params["AutoMinorVersionUpgrade"] = "false"

        if "security_groups" in kwargs:
            if kwargs["security_groups"] is not None:
                for sig in range(len(kwargs["security_groups"])):
                    params['VpcSecurityGroupIds.member.%d' % (sig + 1,)] =\
                        kwargs["security_groups"][sig]

        object = self.connection.request(self.path, params=params).object

        l = object.find(fixxpath(
                xpath='ModifyDBInstanceResult/DBInstance',
                namespace=NAMESPACE))
        return self.to_db_instance(l)

    def reboot_instance(self, db_id):
        params = {
            'Action': 'RebootDBInstance',
            'DBInstanceIdentifier': db_id
         }

        object = self.connection.request(self.path, params=params).object

        l = object.find(fixxpath(
                xpath='RebootDBInstanceResult/DBInstance',
                namespace=NAMESPACE))
        return self.to_db_instance(l)


class RDSSubnetGroup(object):
    """

    """

    def __init__(self, name, vpcid, state, driver, extra=None):
        self.vpcid = vpcid
        self.name = name
        self.state = state
        self.extra = extra or {}
        self.driver = driver

    def __repr__(self):
        return (('<RDSSubnetGroup: name=%s, vpcid=%s, extra=[...]>') % (
                                                    self.name, self.vpcid))


class RDSSecurityGroup(object):
    """

    """

    def __init__(self, name, description, driver, extra=None):
        self.name = name
        self.description = description
        self.extra = extra or {}
        self.driver = driver

    def __repr__(self):
        return (('<RDSSecurityGroup: name=%s, description=%s, extra=[...]>') % (self.name, self.description))


class RDSSnapshot(object):
    """

    """
    def __init__(self, id, db_id, state,
                 allocated, creationdate,
                 driver, extra):
        self.id = id
        self.db_id = db_id
        self.state = state
        self.allocated = allocated
        self.creationdate = creationdate
        self.extra = extra or {}
        self.driver = driver

    def __repr__(self):
        return (('<RDSSnapshots: id=%s, db_id=%s, state=%s, allocated=%s, creationdate=%s, extra=[...]>') % (
                    self.id, self.db_id,
                    self.state, self.allocated, self.creationdate))
