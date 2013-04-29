import datetime
import json
import sys
import time
import os

import prettytable

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))
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

start = datetime.datetime(year=yesterday.year, month=yesterday.month, day=yesterday.day)
end = start + datetime.timedelta(hours=length-1, minutes=59, seconds=59)

instance_map = {}  # { uuid : [request_id, request_id, ...] }
metadata = {'raw_text': True, 'instances': instance_map}
report = [metadata]

#report.append("Generating report for %s to %s" % (start, end))

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

    req_list = []
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

        if diff > 3600 and failure_type == None:
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
            failed_request = {}
            req_list.append(req)
            instance_map[uuid] = req_list
            failed_request['req'] = req
            failed_request['duration'] = "%.2f minutes" % (diff/60)
            failed_request['operation'] = operation
            failed_request['platform'] = image_type.readable(image_type_num)
            failures[key] = failures.get(key, 0) + 1
            tenant_issues[tenant] = tenant_issues.get(tenant, 0) + 1

            if err_id:
                err = models.RawData.objects.get(id=err_id)
                queue, body = json.loads(err.json)
                payload = body['payload']

                #Add error information to failed request report
                failed_request['event_id'] = err.id
                failed_request['tenant'] = err.tenant
                failed_request['service'] = err.service
                failed_request['host'] = err.host
                failed_request['deployment'] = err.deployment.name
                failed_request['event'] = err.event
                failed_request['when'] = str(dt.dt_from_decimal(err.when))

                exc = payload.get('exception')
                if exc:
                    # group the messages ...
                    failed_request['exception'] = exc

                    exc_str = str(exc)
                    error_messages[exc_str] = error_messages.get(exc_str, 0) + 1

                    # extract the code, if any ...
                    code = exc.get('kwargs', {}).get('code')
                    if code:
                        codes[code] = codes.get(code, 0) + 1
                        failure_type = code
                failed_request['failure_type'] = failure_type
                raws = models.RawData.objects.filter(request_id=req)\
                                     .exclude(event='compute.instance.exists')\
                                     .order_by('when')
                failed_request['details'] = []

                for raw in raws:
                    failure_detail = {}
                    failure_detail['host'] = raw.host
                    failure_detail['event'] = raw.event
                    failure_detail['old_state'] = raw.old_state
                    failure_detail['state'] = raw.state
                    failure_detail['old_task'] = raw.old_task
                    failure_detail['task'] = raw.task
                    failed_request['details'].append(failure_detail)

                report.append(failed_request)

            cause_key = (key, failure_type)
            causes[cause_key] = causes.get(cause_key, 0) + 1

values = {'json': json.dumps(report),
          'created': dt.dt_to_decimal(datetime.datetime.utcnow()),
          'period_start': start,
          'period_end': end,
          'version': 1,
          'name': 'Error detail report'}
report = models.JsonReport(**values)
report.save()
