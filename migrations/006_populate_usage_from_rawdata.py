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

from django.core.exceptions import MultipleObjectsReturned

from stacktach import datetime_to_decimal as dt
from stacktach import models
from stacktach import views

if __name__ != '__main__':
    sys.exit(1)

events = ['compute.instance.create.start',
          'compute.instance.create.end',
          'compute.instance.rebuild.start',
          'compute.instance.rebuild.end',
          'compute.instance.resize.prep.start',
          'compute.instance.resize.prep.end',
          'compute.instance.finish_resize.end',
          'compute.instance.resize.revert.start',
          'compute.instance.resize.revert.end',
          'compute.instance.delete.end']


def usage_already_exists(raw):
    if raw.event == 'compute.instance.delete.end':
        # Since deletes only have one event, they either exist or they don't
        try:
            models.InstanceDeletes.objects.get(raw=raw)
        except models.InstanceDeletes.DoesNotExist:
            return False
        except MultipleObjectsReturned:
            return True
        return True
    else:
        # All other usage has multiple events, thus they can exist but be
        # incomplete.
        return False


def populate_usage(raw, body):
    if not usage_already_exists(raw):
        views.aggregate_usage(raw, body)


def print_status(event, completed, errored, total):
    out = (event, completed, errored, total - (completed + errored))
    print "%s: %s completed, %s errored, %s remaining" % out


def find_start_decimal():
    usage = models.InstanceUsage.objects.all().order_by('id')[0]
    usage_raw = models.RawData.objects.filter(request_id=usage.request_id)\
                                      .order_by('when')[0]
    delete = models.InstanceDeletes.objects.all().order_by('id')[0]
    # Start a day after receiving the first usage, just to be safe
    return min(usage_raw.when, delete.raw.when) + (60 * 60 * 24)

start_decimal = find_start_decimal()

print "Starting from date %s" % dt.dt_from_decimal(start_decimal)

for event in events:
    start = datetime.datetime.utcnow()

    raws = models.RawData.objects.filter(event=event, when__lte=start_decimal)
    total = raws.count()
    completed = 0
    errored = 0
    loc = 0

    print_status(event, completed, errored, total)
    update_interval = datetime.timedelta(seconds=30)
    next_update = start + update_interval
    while loc < total:
        new_loc = loc + 500
        for raw in raws[loc:new_loc]:
            try:
                json_dict = json.loads(raw.json)
                populate_usage(raw, json_dict[1])
                completed += 1
            except Exception:
                errored += 1
                print "Error with raw: %s" % raw.id

            if datetime.datetime.utcnow() > next_update:
                print_status(event, completed, errored, total)
                next_update = datetime.datetime.utcnow() + update_interval
        loc = new_loc

    end = datetime.datetime.utcnow()
    print_status(event, completed, errored, total)
    print "%s took %s" % (event, end - start)
