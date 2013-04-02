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
length = 24

start = datetime.datetime(year=yesterday.year, month=yesterday.month, 
                          day=yesterday.day) 
end = start + datetime.timedelta(hours=length-1, minutes=59, seconds=59)

report = [{'raw_text':True}]  # Tell Stacky not to format results.
report.append("Generating report for %s to %s" % (start, end))

dstart = dt.dt_to_decimal(start)
dend = dt.dt_to_decimal(end)

codes = {}

deployments = {}
for deploy in models.Deployment.objects.all():
    deployments[deploy.id] = deploy.name

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
        req = req_dict['request_id']
        raws = list(models.RawData.objects.filter(request_id=req)\
                                     .exclude(event='compute.instance.exists')\
                                     .values("id", "when", "routing_key", "old_state",
                                             "state", "tenant", "event", "image_type",
                                             "deployment")\
                                     .order_by('when'))

        _start = None
        err_id = None
        failure_type = None

        operation = "n/a"
        platform = 0
        tenant = 0
        cell = "n/a"
        image_type_num = 0

        _when = None

        for raw in raws:
            _when = raw['when']
            _routing_key = raw['routing_key']
            _old_state = raw['old_state']
            _state = raw['state']
            _tenant = raw['tenant']
            _event = raw['event']
            _image_type = raw['image_type']
            _name = raw['deployment']
            _id = raw['id']

            if not _start:
                _start = _when

            if 'error' in _routing_key:
                err_id = _id
                failure_type = 'http'

            if _old_state != 'error' and _state == 'error':
                failure_type = 'state'
                err_id = _id

            if _old_state == 'error' and \
                            (not _state in ['deleted', 'error']):
                failure_type = None
                err_id = None

            if _tenant:
                tenant = _tenant

            for cmd in cmds:
                if cmd in _event:
                    operation = cmd
                    cell = deployments.get(_name, "n/a")
                    break

            if _image_type:
                image_type_num |= _image_type

        if not _start:
            continue

        image = "?"
        if image_type.isset(image_type_num, image_type.BASE_IMAGE):
            image = "base"
        if image_type.isset(image_type_num, image_type.SNAPSHOT_IMAGE):
            image = "snap"

        _end = _when
        diff = _end - _start

        if diff > 3600:
            failure_type = ">60"

        key = (operation, image_type_num, cell)

        # Track durations for all attempts, good and bad ...
        duration_min, duration_max, duration_count, duration_total = \
            durations.get(key, (9999999, 0, 0, 0))
        duration_min = min(duration_min, diff)
        duration_max = max(duration_max, diff)
        duration_count += 1
        duration_total += diff
        durations[key] = (duration_min, duration_max, duration_count,
                          duration_total)

        if not failure_type:
            successes[key] = successes.get(key, 0) + 1
        else:
            err = models.RawData.objects.get(id=err_id)
            report.append('')
            report.append("------ %s ----------" % uuid)
            report.append("Req: %s" % req)
            report.append("Duration: %.2f minutes" % (diff / 60))
            report.append("Operation: %s" % operation)
            report.append("Platform: %s" % image_type.readable(image_type_num))
            failures[key] = failures.get(key, 0) + 1
            tenant_issues[tenant] = tenant_issues.get(tenant, 0) + 1

            if err:
                queue, body = json.loads(err.json)
                payload = body['payload']
                
                report.append("Event ID: %s" % err.id)
                report.append("Tenant: %s" % err.tenant)
                report.append("Service: %s" % err.service)
                report.append("Host: %s" % err.host)
                report.append("Deployment: %s" % err.deployment.name)
                report.append("Event: %s" % err.event)
                report.append("When: %s" % dt.dt_from_decimal(err.when))
                exc = payload.get('exception')
                if exc:
                    # group the messages ...
                    exc_str = str(exc)
                    report.append("Exception: %s" % exc_str)
                    error_messages[exc_str] = \
                                        error_messages.get(exc_str, 0) + 1
                    
                    # extract the code, if any ...
                    code = exc.get('kwargs', {}).get('code')
                    if code:
                        codes[code] = codes.get(code, 0) + 1
                        failure_type = code
                report.append("Failure Type: %s" % failure_type)

                report.append('')
                report.append("Details:")
                raws = models.RawData.objects.filter(request_id=req)\
                                     .exclude(event='compute.instance.exists')\
                                     .order_by('when')

                for raw in raws:
                    report.append("H: %s E:%s, S:(%s->%s) T:(%s->%s)" % 
                                    (raw.host, raw.event, 
                                     raw.old_state, raw.state, raw.old_task,
                                     raw.task))
                report.append('---------------------------------------')
            cause_key = (key, failure_type)
            causes[cause_key] = causes.get(cause_key, 0) + 1


def dump_breakdown(totals, label):
    p = prettytable.PrettyTable(["Category", "Count"])
    for k, v in totals.iteritems():
        p.add_row([k, v])
    report.append(label)
    p.sortby = 'Count'
    report.append(p.get_string())


def dump_summary(info, label):
    report.append("-- %s by operation by cell by platform --" % (label,))
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
    report.append(p.get_string())

    dump_breakdown(op_totals, "Total %s by Operation" % label)
    dump_breakdown(cell_totals, "Total %s by Cell" % label)
    dump_breakdown(platform_totals, "Total %s by Platform" % label)

    report.append('')
    return total


good = dump_summary(successes, "Success")
bad = dump_summary(failures, "Failures")
report.append(""" 
SUMMARY

=====================================================
Total Success: %d Total Failure: %d

""" % (good, bad))

p = prettytable.PrettyTable(["Tenant", "Count"])
for tenant, count in tenant_issues.iteritems():
    p.add_row([tenant, count])
p.sortby = 'Count'
report.append("""
-- Errors by Tenant --
%s""" % p.get_string())

p = prettytable.PrettyTable(["Return Code", "Count"])
for k, v in codes.iteritems():
    p.add_row([k, v])
p.sortby = 'Count'
report.append("""
-- Return code counts --
%s""" % p.get_string())

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
report.append("""
-- Cause breakdown --
%s""" % p.get_string())

p = prettytable.PrettyTable(["Count", "Message"])
for k, v in error_messages.iteritems():
    p.add_row([v, k[:80]])
p.sortby = 'Count'
report.append("""
-- Error Message Counts --
%s""" % p.get_string())

for r in report[1:]:
    print r

values = {'json': json.dumps(report),
          'created': dt.dt_to_decimal(datetime.datetime.utcnow()),
          'period_start': start,
          'period_end': end,
          'version': 1,
          'name': 'Error detail report'}
report = models.JsonReport(**values)
report.save()
