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

hours = 0
length = 6

start = datetime.datetime(year=yesterday.year, month=yesterday.month, 
                          day=yesterday.day) 
end = start + datetime.timedelta(hours=length-1, minutes=59, seconds=59)

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
causes = {}
durations = {}
error_messages = {}
successes = {}
tenant_issues = {}

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
        platform = 0
        tenant = 0
        cell = "unk"

        for raw in raws:
            if not start:
                start = raw.when
            if 'error' in raw.routing_key:
                err = raw
                report = True

            if raw.tenant:
                if tenant > 0 and raw.tenant != tenant:
                    print "Conflicting tenant ID", raw.tenant, tenant
                tenant = raw.tenant

            for cmd in cmds:
                if cmd in raw.event:
                    operation = cmd
                    cell = raw.deployment.name
                    break

            if raw.image_type > 0:
                platform = raw.image_type

        if not start:
            continue

        end = raw.when
        diff = end - start

        if diff > 3600:
            report = True

        key = (operation, platform, cell)

        # Track durations for all attempts, good and bad ...
        duration_min, duration_max, duration_count, duration_total = \
            durations.get(key, (9999999, 0, 0, 0))
        duration_min = min(duration_min, diff)
        duration_max = max(duration_max, diff)
        duration_count += 1
        duration_total += diff
        durations[key] = (duration_min, duration_max, duration_count,
                          duration_total)

        if not report:
            successes[key] = successes.get(key, 0) + 1
        else:
            print "------", uuid, "----------"
            print "    Req:", req
            print "    Duration: %.2f minutes" % (diff / 60)
            print "    Operation:", operation
            print "    Platform:", image_type.readable(platform)
            cause = "> %d min" % (expiry / 60)
            failures[key] = failures.get(key, 0) + 1
            tenant_issues[tenant] = tenant_issues.get(tenant, 0) + 1

            if err:
                queue, body = json.loads(err.json)
                payload = body['payload']
                print "Error. EventID: %s, Tenant %s, Service %s, Host %s, "\
                      "Deployment %s, Event %s, When %s"\
                    % (err.id, err.tenant, err.service, err.host, 
                       err.deployment.name, 
                       err.event, dt.dt_from_decimal(err.when))
                exc = payload.get('exception')
                if exc:
                    # group the messages ...
                    exc_str = str(exc)
                    print exc_str
                    error_messages[exc_str] = \
                                        error_messages.get(exc_str, 0) + 1
                    
                    # extract the code, if any ...
                    code = exc.get('kwargs', {}).get('code')
                    if code:
                        codes[code] = codes.get(code, 0) + 1
                        cause = code
            cause_key = (key, cause)
            causes[cause_key] = causes.get(cause_key, 0) + 1


def dump_breakdown(totals, label):
    p = prettytable.PrettyTable(["Category", "Count"])
    for k, v in totals.iteritems():
        p.add_row([k, v])
    print label
    p.sortby = 'Count'
    print p




def dump_summary(info, label):
    print "-- %s by operation by cell by platform --" % (label,)
    p = prettytable.PrettyTable(["Operation", "Cell", "Platform", "Count",
                                 "Min", "Max", "Avg"])
    for c in ["Count", "Min", "Max", "Avg"]:
        p.align[c] = 'r'

    total = 0
    op_totals = {}
    cell_totals = {}
    platform_totals = {}
    for key, count in info.iteritems():
        operation, platform, cell = key
        readable = image_type.readable(platform)
        text = "n/a"
        if readable:
            text = ", ".join(readable)

        _min, _max, _count, _total = durations[key]
        _avg = float(_total) / float(_count)
        _fmin = dt.sec_to_str(_min)
        _fmax = dt.sec_to_str(_max)
        _favg = dt.sec_to_str(_avg * 100.0)

        op_totals[operation] = op_totals.get(operation, 0) + count
        cell_totals[cell] = cell_totals.get(cell, 0) + count
        platform_totals[text] = platform_totals.get(text, 0) + count

        p.add_row([operation, cell, text, count, _fmin, _fmax, _favg])
        total += count
    p.sortby = 'Count'
    print p

    dump_breakdown(op_totals, "Total %s by Operation" % label)
    dump_breakdown(cell_totals, "Total %s by Cell" % label)
    dump_breakdown(platform_totals, "Total %s by Platform" % label)

    print

    return total


print 
print "SUMMARY"
print
good = dump_summary(successes, "Success")
bad = dump_summary(failures, "Failures")
print "====================================================="
print "Total Success: %d Total Failure: %d" % (good, bad)
print

print "-- Errors by Tenant --"
p = prettytable.PrettyTable(["Tenant", "Count"])
for tenant, count in tenant_issues.iteritems():
    p.add_row([tenant, count])
p.sortby = 'Count'
print p

print
print "-- Return code counts --"
p = prettytable.PrettyTable(["Return Code", "Count"])
for k, v in codes.iteritems():
    p.add_row([k, v])
p.sortby = 'Count'
print p

print
print "-- Cause breakdown --"
p = prettytable.PrettyTable(["Cause", "Operation", "Cell", "Platform", "Count"])
for cause_key, count in causes.iteritems():
    key, cause = cause_key
    operation, platform, cell = key
    readable = image_type.readable(platform)
    text = "n/a"
    if readable:
        text = ", ".join(readable)
    p.add_row([cause, operation, cell, text, count])
p.sortby = 'Count'
print p

print
print "-- Error Message Counts --"
p = prettytable.PrettyTable(["Count", "Message"])
for k, v in error_messages.iteritems():
    p.add_row([v, k[:80]])
p.sortby = 'Count'
print p

