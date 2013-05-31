import datetime
import json
import sys
import time
import os
import re

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))
from stacktach import datetime_to_decimal as dt
from stacktach import image_type
from stacktach import models


if __name__ != '__main__':
    sys.exit(1)


# To mask unique identifiers for categorizing notifications
def mask_msg(text):
    masking_regex = (
        (1, 'REQ_ID',
         r"req-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
         ),
        (2, 'UUID',
         r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
         ),
        (3, 'HOST_ADDRESS',
         r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
         ),
        (4, 'LG_NUM',
         r"\b\d{3}\d+\b"
         )
    )
    masked = str(text)
    for config in masking_regex:
        masked = re.sub(config[2], "$%s" % str(config[1]), masked)
    return masked


# Assemble message from exception object
def build_exc_msg(exc=None, separator=", "):

    """
    White-list exception components we're aware of, and leave a catch all;
    because of freeform exception objects from notifications.
    """

    if exc is None:
        return exc

    message = []
    if exc.get('kwargs', False):
        kwargs = exc['kwargs']
        if kwargs.get('value', False):
            value = kwargs['value']
            trcbk_index = value.rfind("Traceback")
            if trcbk_index > 0:
                value = str(value[:trcbk_index]) + "$TRACEBACK"
            message.append("value: %s" % value)

        # kwargs: generic message components that don't require more filter
        misc_list = ['reason', 'method', 'topic', 'exc_type',
                     'actual', 'code']
        for key in misc_list:
            if kwargs.get(key, False):
                message.append("%s: %s" % (key, kwargs[key]))
        # END generic message components in kwargs

        if kwargs.get('expected', False):
            message.append("expected: %s" % kwargs['expected'][0])

    if exc.get('details', False):
        details = exc['details']
        if type(details) is list:
            for item in details:
                message.append(str(item))
        elif type(details) is dict:
            for k, v in details.iteritems():
                message.append("%s: %s" % (k, v))
        elif type(details) is str:
            message.append(details)

    # exc: generic messages that don't require more filter
    misc_list = ['message', 'cmd', 'stderr', 'exit_code',
                 'code', 'description']
    for key in misc_list:
        if exc.get(key, False):
            message.append("%s: %s" % (key, exc[key]))

    if exc.get('stdout', False):
        if exc['stdout'] != "":
            message.append("stdout: %s" % exc['stdout'])
    #END generic message components in exc

    if len(message) == 0:
        for k, v in exc.iteritems():
            message.append("%s: %s" % (k, v))
    return separator.join(message)

if __name__ == '__main__':

    # Start report
    yesterday = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)
    if len(sys.argv) == 2:
        try:
            t = time.strptime(sys.argv[1], "%Y-%m-%d")
            yesterday = datetime.datetime(*t[:6])
        except Exception, e:
            print e
            print "Usage: python error_details.py YYYY-MM-DD (the end date)"
            sys.exit(1)

    hours = 0
    length = 24

    start = datetime.datetime(year=yesterday.year, month=yesterday.month,
                              day=yesterday.day)
    end = start + datetime.timedelta(hours=length-1, minutes=59, seconds=59)

    instance_map = {}  # { uuid : [request_id, request_id, ...] }
    exception_counts = {}  # { exception_message : count }
    event_counts = {}  # { event_name : count }
    metadata = {'report_format': 'json',
                'instances': instance_map,
                'exception_counts': exception_counts,
                'event_counts': event_counts
                }

    # Tell Stacky to format as JSON and set placeholders for various summaries
    report = [metadata]

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
    successes = {}
    tenant_issues = {}

    for uuid_dict in updates:
        uuid = uuid_dict['instance']

        # All the unique Request ID's for this instance during that timespan.
        reqs = models.RawData.objects.filter(instance=uuid,
                                             when__gt=dstart, when__lte=dend)\
                                     .values('request_id').distinct()

        req_list = []
        for req_dict in reqs:
            req = req_dict['request_id']

            raws = list(models.RawData.objects.filter(request_id=req)
                        .exclude(event='compute.instance.exists')
                        .values("id", "when", "routing_key", "old_state",
                                "state", "tenant", "event", "image_type",
                                "deployment")
                        .order_by('when'))

            _start = None
            _when = None

            err_id = None
            failure_type = None
            operation = "n/a"
            platform = 0
            tenant = 0
            cell = "n/a"
            image_type_num = 0

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

                if failure_type != 'state' and _old_state != 'error' and\
                                                             _state == 'error':
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

            if diff > 3600 and failure_type is None:
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
                message = []  # For exception message masking
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

                    # Add error information to failed request report
                    failed_request['event_id'] = err.id
                    failed_request['tenant'] = err.tenant
                    failed_request['service'] = err.service
                    failed_request['host'] = err.host
                    failed_request['deployment'] = err.deployment.name
                    failed_request['event'] = err.event
                    failed_request['when'] = str(dt.dt_from_decimal(err.when))

                    # Track failed event counts
                    event_counts[err.event] = event_counts.get(err.event, 0) + 1

                    exc = payload.get('exception')
                    if exc:
                        # group the messages ...
                        failed_request['exception'] = exc

                        # assemble message from exception and generalize
                        message_str = mask_msg(build_exc_msg(exc))
                        # count exception messages
                        exception_counts[message_str] = exception_counts.get(
                            message_str, 0) + 1

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

    # print exception counts in report metadata
    print json.dumps(report[0]['exception_counts'], indent=4)

    # print event counts in report metadata
    print json.dumps(report[0]['event_counts'], indent=4)

    # Assign values to store in DB
    values = {'json': json.dumps(report),
              'created': dt.dt_to_decimal(datetime.datetime.utcnow()),
              'period_start': start,
              'period_end': end,
              'version': 1,
              'name': 'Error detail report'}
    json_report = models.JsonReport(**values)
    json_report.save()
