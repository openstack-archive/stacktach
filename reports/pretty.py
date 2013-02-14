import datetime
import json
import sys
import time

import prettytable

sys.path.append("/stacktach")

from stacktach import datetime_to_decimal as dt
from stacktach import image_type
from stacktach import models


if __name__ != '__main__':
    sys.exit(1)

yesterday = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)
if len(sys.argv) == 2:
    try:
        t = time.strptime(sys.argv[1], "%Y-%m-%d")
        yesterday = datetime.datetime(*t[:6])
    except Exception, e:
        print e
        print "Usage: python requests.py YYYY-MM-DD (the end date)"
        sys.exit(1)

percentile = 90
hours = 24

start = datetime.datetime(year=yesterday.year, month=yesterday.month, 
                          day=yesterday.day) 
end = start + datetime.timedelta(hours=hours-1, minutes=59, seconds=59)

print "Generating report for %s to %s" % (start, end)

dstart = dt.dt_to_decimal(start)
dend = dt.dt_to_decimal(end)

codes = {}

# Get all the instances that have changed in the last N hours ...
updates = models.RawData.objects.filter(event='compute.instance.update',
                                        when__gt=dstart, when__lte=dend)\
                                .values('instance').distinct()

expiry = 60 * 60  # 1 hour
cmds = ['create', 'rebuild', 'rescue', 'resize', 'snapshot']

failures = {}
durations = {}
attempts = {}

for uuid_dict in updates:
    uuid = uuid_dict['instance']

    # All the unique Request ID's for this instance during that timespan.
    reqs = models.RawData.objects.filter(instance=uuid,
                                         when__gt=dstart, when__lte=dend) \
                                 .values('request_id').distinct()


    for req_dict in reqs:
        report = False
        req = req_dict['request_id']
        raws = models.RawData.objects.filter(request_id=req)\
                                     .exclude(event='compute.instance.exists')\
                                     .order_by('when')

        start = None
        err = None

        operation = "aux"
        image_type_num = 0

        for raw in raws:
            if not start:
                start = raw.when
            if 'error' in raw.routing_key:
                err = raw
                report = True

            for cmd in cmds:
                if cmd in raw.event:
                    operation = cmd
                    break

            if raw.image_type:
                image_type_num |= raw.image_type                 

        image = "?"
        if image_type.isset(image_type_num, image_type.BASE_IMAGE):
            image = "base"
        if image_type.isset(image_type_num, image_type.SNAPSHOT_IMAGE):
            image = "snap"

        if not start:
            continue

        end = raw.when
        diff = end - start

        if diff > 3600:
            report = True

        key = (operation, image)

        # Track durations for all attempts, good and bad ...
        _durations = durations.get(key, [])
        _durations.append(diff)
        durations[key] = _durations

        attempts[key] = attempts.get(key, 0) + 1

        if report:
            failures[key] = failures.get(key, 0) + 1

# Print the results ...
cols = ["Operation", "Image", "Min*", "Max*", "Avg*",
        "Requests", "# Fail", "Fail %"]
p = prettytable.PrettyTable(cols)
for c in cols[2:]:
    p.align[c] = 'r'
p.sortby = cols[0]

pct = (float(100 - percentile) / 2.0) / 100.0
print "* Using %d-th percentile for results (+/-%.1f%% cut)" % \
                            (percentile, pct * 100.0)
total = 0
failure_total = 0
for key, count in attempts.iteritems():
    total += count
    operation, image = key

    failure_count = failures.get(key, 0)
    failure_total += failure_count
    failure_percentage = float(failure_count) / float(count)
    _failure_percentage = "%.1f%%" % (failure_percentage * 100.0)

    # N-th % of durations ...
    _values = durations[key]
    _values.sort()
    _outliers = int(float(len(_values)) * pct)
    if _outliers > 0:
        before = len(_values)
        _values = _values[_outliers:-_outliers]
        print "culling %d -> %d" % (before, len(_values))
    _min = 99999999
    _max = 0
    _total = 0.0
    for value in _values:
        _min = min(_min, value)
        _max = max(_max, value)
        _total += float(value)
    _avg = float(_total) / float(len(_values))
    _fmin = dt.sec_to_str(_min)
    _fmax = dt.sec_to_str(_max)
    _favg = dt.sec_to_str(_avg)

    p.add_row([operation, image, _fmin, _fmax, _favg, count, 
               failure_count, _failure_percentage])
print p

print "Total: %d, Failures: %d, Failure Rate: %.1f%%" % \
                (total, failure_total, 
                    (float(failure_total)/float(total)) * 100.0)
