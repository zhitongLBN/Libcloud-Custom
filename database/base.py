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
    'DatabaseNodeDriver'
]


class DatabaseNodeDriver(BaseDriver):

    """
    A base DatabaseDriver class to derive from

    This class is always subclassed by a specific driver.

    """

    connectionCls = ConnectionKey
    name = None
    type = None
    port = None

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 **kwargs):
        super(DatabaseNodeDriver, self).__init__(key=key, secret=secret,
                                                 secure=secure, host=host,
                                                 port=port, **kwargs)


class DBInstance(object):

    def __init__(self, name, id, status, engine, engine_version, creation_date,
                 allocated, size, user, location, driver, description=None,
                 extra=None):

        self.name = name
        self.id = id
        self.status = status
        self.engine = engine
        self.engine_version = engine_version
        self.creation_date = creation_date
        self.allocated = allocated
        self.size = size
        self.user = user
        self.location = location
        self.description = description or ""
        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        return (('<DBInstance: id=%s, name=%s, engine=%s, '
                 'engine_version=%s, '
                 'status=%s, creation_date=%s, '
                 'size=%s, allocated=%s, user=%s, '
                 'location=%s, driver=%s extra={...} ...>')
                % (self.id,
                   self.name,
                   self.engine,
                   self.engine_version,
                   self.status,
                   self.creation_date,
                   self.size,
                   self.allocated,
                   self.user,
                   self.location,
                   self.driver))


class DBEngine(object):

    def __init__(self, dbms, family, version, driver, description=None,
                 version_description=None, extra=None):
        self.dbms = dbms
        self.family = family
        self.version = version
        self.description = description or ""
        self.version_description = version_description or ""
        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        return (('<DBEngine: dbms=%s, family=%s, version=%s, '
                 'driver=%s extra={...} ...>')
                % (self.dbms,
                   self.family,
                   self.version,
                   self.driver))
