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
import json
import sys

sys.path.append("/stacktach")

from stacktach import datetime_to_decimal as dt
from stacktach import image_type
from stacktach import models


if __name__ != '__main__':
    sys.exit(1)

states = {}


def fix_chunk(hours, length):
    now = datetime.datetime.utcnow()
    start = now - datetime.timedelta(hours=hours+length)
    end = now - datetime.timedelta(hours=hours)
    dstart = dt.dt_to_decimal(start)
    dend = dt.dt_to_decimal(end)

    done = 0
    updated = 0
    block = 0
    print "Hours ago (%d to %d) %d - %d" % (hours + length, hours, dstart, dend)
    updates = models.RawData.objects.filter(event='compute.instance.update',
                                            when__gt=dstart, when__lte=dend)\
                                    .only('task', 'image_type', 'json')

    for raw in updates:
        queue, body = json.loads(raw.json)
        payload = body.get('payload', {})
        task = payload.get('new_task_state', None)

        if task != None and task != 'None':
            states[task] = states.get(task, 0) + 1
            raw.task = task

        raw.image_type = image_type.get_numeric_code(payload, raw.image_type)
        updated += 1
        raw.save()

        done += 1
        if done >= 10000:
            block += 1
            done = 0
            print "# 10k blocks processed: %d (events %d)" % \
                                        (block, updated)
            updated = 0

    for kv in states.iteritems():
        print "%s = %d" % kv

for day in xrange(0, 90):
    hours = day * 24
    steps = 12
    chunk = 24 / steps
    for x in xrange(steps):
        fix_chunk(hours, chunk)
        hours += chunk
