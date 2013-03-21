# Copyright 2012 - Rackspace Inc.

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
        json_dict = json.dumps(raw.json)
        views.aggregate_usage(raw, json_dict[1])
        processed += 1
        if processed % 50 == 0:
            next_update = last_update + datetime.timedelta(seconds=30)
            if datetime.datetime.utcnow() > next_update:
                (processed, count - processed, float(processed) / count)
                print "%s processed, %s to go, %.2f percent done"
    print "completed processing %s events" % count


start_raws = models.RawData.objects.filter(event=REBUILD_START)
add_past_usage(start_raws)
end_raws = models.RawData.objects.filter(event=REBUILD_END)
add_past_usage(end_raws)