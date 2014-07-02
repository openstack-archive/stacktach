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
import datetime
import os
import sys

try:
    import ujson as json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        import json

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from stacktach import models
from stacktach import utils


if __name__ != '__main__':
    sys.exit(1)


def print_update(total, completed, errored):
    to_go = total - (completed + errored)
    print "%s populated, %s to go, %s errored" % (completed, to_go, errored)

filters = {
    'audit_period_beginning__exact': None,
    'audit_period_ending__exact': None
}
exists = models.InstanceExists.objects.filter(**filters)

count = exists.count()
start = datetime.datetime.utcnow()
print "%s records to populate" % count

update_interval = datetime.timedelta(seconds=30)
next_update = start + update_interval

completed = 0
errored = 0
for exist in exists:
    try:
        notif = json.loads(exist.raw.json)
        payload = notif[1]['payload']
        beginning = utils.str_time_to_unix(payload['audit_period_beginning'])
        exist.audit_period_beginning = beginning
        ending = utils.str_time_to_unix(payload['audit_period_ending'])
        exist.audit_period_ending = ending
        exist.save()
        completed += 1
    except:
        print "Error with raw %s" % exist.id
        errored += 1

    if datetime.datetime.utcnow() > next_update:
        print_update(count, completed, errored)
        next_update = datetime.datetime.utcnow() + update_interval
