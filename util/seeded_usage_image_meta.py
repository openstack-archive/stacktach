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
import os
import sys

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from stacktach import models

if __name__ != '__main__':
    sys.exit(1)

seed_usage = models.InstanceUsage.objects.filter(request_id=None)
deleted_instances = models.InstanceDeletes.objects.values('instance').distinct()

deleted = set()
for instance in deleted_instances:
    deleted.add(instance['instance'])

fixed = 0

for usage in seed_usage:
    if usage.instance not in deleted and usage.launched_at is not None and \
            usage.launched_at is not '':
        filters = {
            'instance': usage.instance,
            'launched_at__gte': int(usage.launched_at),
            'launched_at__lt': int(usage.launched_at) + 1,
            'status': models.InstanceExists.VERIFIED
        }
        exists = models.InstanceExists.objects.filter(**filters)
        if exists.count() > 0:
            fixed += 1
            usage.os_architecture = exists[0].os_architecture
            usage.os_distro = exists[0].os_distro
            usage.os_version = exists[0].os_version
            usage.rax_options = exists[0].rax_options
            usage.save()
        else:
            print "Couldn't find verified exists for instance %s" % usage.instance

print "Populated %s usage records" % fixed
