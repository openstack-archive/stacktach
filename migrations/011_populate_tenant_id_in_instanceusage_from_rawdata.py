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


def add_past_usages(instance_tenant_id_maps):
    update_count = 0
    for map in instance_tenant_id_maps:
        update_count += models.InstanceUsage.objects.filter(instance=map['instance']).update(tenant=map['tenant'])
    print "updated %s rows" % update_count

distinct_usage_instances = models.InstanceUsage.objects.all().values('instance').distinct()
instance_tenant_id_maps = models.RawData.objects.filter(instance__in=distinct_usage_instances).distinct().values('instance', 'tenant')
add_past_usages(instance_tenant_id_maps)
