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

from libcloud.common.types import LibcloudError

__all__ = [
    "Provider",
    "LibcloudDatabaseError",
]


class LibcloudDatabaseError(LibcloudError):
    pass


class Provider(object):
    RDS = 'aws_rds'


class KeyPairError(LibcloudError):
    error_type = 'KeyPairError'

    def __init__(self, name, driver):
        self.name = name
        self.value = 'Key pair with name %s does not exist' % (name)
        super(KeyPairError, self).__init__(value=self.value, driver=driver)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return ('<%s name=%s, value=%s, driver=%s>' %
                (self.error_type, self.name, self.value, self.driver.name))


class KeyPairDoesNotExistError(KeyPairError):
    error_type = 'KeyPairDoesNotExistError'
