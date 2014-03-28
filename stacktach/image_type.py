# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from operator import itemgetter


BASE_IMAGE = 0x1
SNAPSHOT_IMAGE = 0x2
IMPORT_IMAGE = 0x3

LINUX_IMAGE = 0x10
WINDOWS_IMAGE = 0x20
FREEBSD_IMAGE = 0x40

OS_UBUNTU = 0x100
OS_DEBIAN = 0x200
OS_CENTOS = 0x400
OS_RHEL = 0x800


def isset(num, flag):
    if not num:
        return False
    return num & flag > 0


flags = {'base' : BASE_IMAGE,
         'snapshot' : SNAPSHOT_IMAGE,
         'linux' : LINUX_IMAGE,
         'windows': WINDOWS_IMAGE,
         'freebsd': FREEBSD_IMAGE,
         'ubuntu' : OS_UBUNTU,
         'debian' : OS_DEBIAN,
         'centos' : OS_CENTOS,
         'rhel' : OS_RHEL}


def readable(num):
    result = []
    for k, v in sorted(flags.iteritems(), key=itemgetter(1)):
        if isset(num, v):
            result.append(k)
    return result


def get_numeric_code(payload, default=0):
    meta = payload.get('image_meta', {})
    num = default

    image_type = meta.get('image_type', '')
    if image_type == 'base':
        num |= BASE_IMAGE
    if image_type == 'snapshot':
        num |= SNAPSHOT_IMAGE
    if image_type == 'import':
        num |= IMPORT_IMAGE
    os_type = meta.get('os_type', payload.get('os_type', ''))
    if os_type == 'linux':
        num |= LINUX_IMAGE
    if os_type == 'windows':
        num |= WINDOWS_IMAGE
    if os_type == 'freebsd':
        num |= FREEBSD_IMAGE

    os_distro = meta.get('os_distro', '')
    if os_distro == 'ubuntu':
        num |= OS_UBUNTU
    if os_distro == 'debian':
        num |= OS_DEBIAN
    if os_distro == 'centos':
        num |= OS_CENTOS
    if os_distro == 'rhel':
        num |= OS_RHEL

    return num
