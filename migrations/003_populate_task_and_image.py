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
