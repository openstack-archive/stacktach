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
from stacktach import views

if __name__ != '__main__':
    sys.exit(1)

REBUILD_START = 'compute.instance.rebuild.start'
REBUILD_END = 'compute.instance.rebuild.end'


def add_past_usage(raws):

    count = raws.count()
    processed = 0
    print "%s events to be processed" % count
    last_update = datetime.datetime.utcnow()
    for raw in raws:
        json_dict = json.loads(raw.json)
        views.aggregate_usage(raw, json_dict[1])
        processed += 1
        if processed % 50 == 0:
            next_update = last_update + datetime.timedelta(seconds=30)
            if datetime.datetime.utcnow() > next_update:
                m = (processed, count - processed,
                     (float(processed) / count)*100)
                print "%s processed, %s to go, %.2f percent done" % m
                last_update = datetime.datetime.utcnow()
    print "completed processing %s events" % count


start_raws = models.RawData.objects.filter(event=REBUILD_START)
add_past_usage(start_raws)
end_raws = models.RawData.objects.filter(event=REBUILD_END)
add_past_usage(end_raws)
