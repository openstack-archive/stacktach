import decimal
import datetime
import json

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

import datetime_to_decimal as dt
import models
import views

SECS_PER_HOUR = 60 * 60
SECS_PER_DAY = SECS_PER_HOUR * 24


def get_event_names():
    return models.RawData.objects.values('event').distinct()


def get_host_names():
    # TODO: We need to upgrade to Django 1.4 so we can get tenent id and
    # host and just do distinct on host name.
    # like: values('host', 'tenant_id').distinct('host')
    # This will be more meaningful. Host by itself isn't really.
    return models.RawData.objects.values('host').distinct()


def routing_key_type(key):
    if key.endswith('error'):
        return 'E'
    return  ' '


def get_deployments():
    return models.Deployment.objects.all().order_by('name')


def get_timings_for_uuid(uuid):
    lifecycles = models.Lifecycle.objects.filter(instance=uuid)

    results = []
    results.append(["?", "Event", "Time (secs)"])
    for lc in lifecycles:
        timings = models.Timing.objects.filter(lifecycle=lc)
        if not timings:
            continue
        for t in timings:
            state = "?"
            show_time = 'n/a'
            if t.start_raw:
                state = 'S'
            if t.end_raw:
                state = 'E'
            if t.start_raw and t.end_raw:
                state = "."
                show_time = sec_to_time(t.diff)
            results.append([state, t.name, show_time])
    return results


def sec_to_time(diff):
    seconds = int(diff)
    usec = diff - seconds
    days = seconds / SECS_PER_DAY
    seconds -= (days * SECS_PER_DAY)
    hours = seconds / SECS_PER_HOUR
    seconds -= (hours * SECS_PER_HOUR)
    minutes = seconds / 60
    seconds -= (minutes * 60)
    usec = str(usec)[1:4]
    return "%dd %02d:%02d:%02d%s" % (days, hours, minutes, seconds, usec)


def rsp(data):
    return HttpResponse(json.dumps(data), content_type="application/json")


def do_deployments(request):
    deployments = get_deployments()
    results = []
    results.append(["#", "Name"])
    for deployment in deployments:
        results.append([deployment.id, deployment.name])
    return rsp(results)


def do_events(request):
    events = get_event_names()
    results = []
    results.append(["Event Name"])
    for event in events:
        results.append([event['event']])
    return rsp(results)


def do_hosts(request):
    hosts = get_host_names()
    results = []
    results.append(["Host Name"])
    for host in hosts:
        results.append([host['host']])
    return rsp(results)


def do_uuid(request):
    uuid = str(request.GET['uuid'])
    related = models.RawData.objects.select_related(). \
                        filter(instance=uuid).order_by('when')
    results = []
    results.append(["#", "?", "When", "Deployment", "Event", "Host",
                        "State", "State'", "Task'"])
    for e in related:
        when = dt.dt_from_decimal(e.when)
        results.append([e.id, routing_key_type(e.routing_key), str(when),
                                        e.deployment.name, e.event,
                                        e.host,
                                        e.state, e.old_state, e.old_task])
    return rsp(results)


def do_timings_uuid(request):
    uuid = request.GET['uuid']
    return rsp(get_timings_for_uuid(uuid))


def do_timings(request):
    name = request.GET['name']
    results = []
    results.append([name, "Time"])
    timings = models.Timing.objects.select_related().filter(name=name) \
                                 .exclude(Q(start_raw=None) | Q(end_raw=None)) \
                                 .order_by('diff')

    for t in timings:
        results.append([t.lifecycle.instance, sec_to_time(t.diff)])
    return rsp(results)


def do_summary(request):
    events = get_event_names()
    interesting = []
    for e in events:
        ev = e['event']
        if ev.endswith('.start'):
            interesting.append(ev[:-len('.start')])

    results = []
    results.append(["Event", "N", "Min", "Max", "Avg"])

    for name in interesting:
        timings = models.Timing.objects.filter(name=name) \
                               .exclude(Q(start_raw=None) | Q(end_raw=None)) \
                               .exclude(diff__lt=0)
        if not timings:
            continue

        total, _min, _max = 0.0, None, None
        num = len(timings)
        for t in timings:
            seconds = float(t.diff)
            total += seconds
            if _min is None:
                _min = seconds
            if _max is None:
                _max = seconds
            _min = min(_min, seconds)
            _max = max(_max, seconds)

        results.append([name, int(num), sec_to_time(_min),
                   sec_to_time(_max), sec_to_time(int(total/num)) ])
    return rsp(results)


def do_request(request):
    request_id = request.GET['request_id']
    events = models.RawData.objects.filter(request_id=request_id) \
                                   .order_by('when')
    results = []
    results.append(["#", "?", "When", "Deployment", "Event", "Host",
                        "State", "State'", "Task'"])
    for e in events:
        when = dt.dt_from_decimal(e.when)
        results.append([e.id, routing_key_type(e.routing_key), str(when),
                                            e.deployment.name, e.event,
                                            e.host, e.state,
                                            e.old_state, e.old_task])
    return rsp(results)


def do_show(request, event_id):
    event_id = int(event_id)
    results = []
    event = None
    try:
        event = models.RawData.objects.get(id=event_id)
    except models.RawData.ObjectDoesNotExist:
        return results

    results.append(["Key", "Value"])
    results.append(["#", event.id])
    when = dt.dt_from_decimal(event.when)
    results.append(["When", str(when)])
    results.append(["Deployment", event.deployment.name])
    results.append(["Category", event.routing_key])
    results.append(["Publisher", event.publisher])
    results.append(["State", event.state])
    results.append(["Event", event.event])
    results.append(["Service", event.service])
    results.append(["Host", event.host])
    results.append(["UUID", event.instance])
    results.append(["Req ID", event.request_id])

    final = [results, ]
    j = json.loads(event.json)
    final.append(json.dumps(j, indent=2))
    final.append(event.instance)

    return rsp(final)


def do_watch(request, deployment_id):
    deployment_id = int(deployment_id)
    since = request.GET.get('since')
    event_name = request.GET.get('event_name')

    deployment_map = {}
    for d in get_deployments():
        deployment_map[d.id] = d
    events = get_event_names()
    max_event_width = max([len(event['event']) for event in events])
    hosts = get_host_names()
    max_host_width = max([len(host['host']) for host in hosts])

    base_events = models.RawData.objects.order_by('when')
    if deployment_id > 0:
        base_events = base_events.filter(deployment=deployment_id)

    if event_name:
        base_events = base_events.filter(event=event_name)

    # Ok, this may seem a little wonky, but I'm clamping the
    # query time to the closest second. The implication is we
    # may not return the absolute latest data (which will have
    # to wait for the next query). The upside of doing this
    # is we can effectively cache the responses. So, with a
    # caching proxy server we can service a lot more clients
    # without having to worry about microsecond differences
    # causing cache misses.

    now = datetime.datetime.utcnow()
    now = now.replace(microsecond=0)  # clamp it down.
    dec_now = dt.dt_to_decimal(now)
    if since:
        since = decimal.Decimal(since)
    else:
        since = now - datetime.timedelta(seconds=2)
        since = dt.dt_to_decimal(since)
    base_events = base_events.filter(when__gt=since)
    events = base_events.filter(when__lte=dec_now)

    c = [10, 1, 15, 20, max_event_width, 36]
    header = ("+%s" * len(c)) + "+"
    splat = header.replace("+", "|")

    results = []

    for raw in events:
        uuid = raw.instance
        if not uuid:
            uuid = "-"
        typ = routing_key_type(raw.routing_key)
        when = dt.dt_from_decimal(raw.when)
        results.append([raw.id, typ,
                       str(when.date()), str(when.time()),
                       deployment_map[raw.deployment.id].name,
                       raw.event,
                       uuid])

    return rsp([c, results, str(dec_now)])


def do_kpi(request, tenant_id=None):
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    yesterday = dt.dt_to_decimal(yesterday)
    trackers = models.RequestTracker.objects.select_related() \
                                   .exclude(last_timing=None)  \
                                   .exclude(start__lt=yesterday) \
                                   .order_by('duration')

    results = []
    results.append(["Event", "Time", "UUID", "Deployment"])
    for track in trackers:
        end_event = track.last_timing.end_raw
        event = end_event.event[:-len(".end")]
        uuid = track.lifecycle.instance
        if tenant_id == None or (tenant_id == end_event.tenant):
            results.append([event, sec_to_time(track.duration),
                   uuid, end_event.deployment.name])
    return rsp(results)


def do_list_usage_launches(request):

    filter_args = {}
    if 'instance' in request.GET:
        filter_args['instance'] = request.GET['instance']

    if len(filter_args) > 0:
        launches = models.InstanceUsage.objects.filter(**filter_args)
    else:
        launches = models.InstanceUsage.objects.all()

    results = []
    results.append(["UUID", "Launched At", "Instance Type Id"])

    for launch in launches:
        launched = None
        if launch.launched_at:
            launched = str(dt.dt_from_decimal(launch.launched_at))
        results.append([launch.instance, launched, launch.instance_type_id])

    return rsp(results)


def do_list_usage_deletes(request):

    filter_args = {}
    if 'instance' in request.GET:
        filter_args['instance'] = request.GET['instance']

    if len(filter_args) > 0:
        deletes = models.InstanceDeletes.objects.filter(**filter_args)
    else:
        deletes = models.InstanceDeletes.objects.all()

    results = []
    results.append(["UUID", "Launched At", "Deleted At"])

    for delete in deletes:
        launched = None
        if delete.launched_at:
            launched = str(dt.dt_from_decimal(delete.launched_at))
        deleted = None
        if delete.deleted_at:
            deleted = str(dt.dt_from_decimal(delete.deleted_at))
        results.append([delete.instance, launched, deleted])

    return rsp(results)


def do_list_usage_exists(request):

    filter_args = {}
    if 'instance' in request.GET:
        filter_args['instance'] = request.GET['instance']

    if len(filter_args) > 0:
        exists = models.InstanceExists.objects.filter(**filter_args)
    else:
        exists = models.InstanceExists.objects.all()

    results = []
    results.append(["UUID", "Launched At", "Deleted At", "Instance Type Id",
                    "Message ID", "Status"])

    for exist in exists:
        launched = None
        if exist.launched_at:
            launched = str(dt.dt_from_decimal(exist.launched_at))
        deleted = None
        if exist.deleted_at:
            deleted = str(dt.dt_from_decimal(exist.deleted_at))
        results.append([exist.instance, launched, deleted,
                        exist.instance_type_id, exist.message_id,
                        exist.status])

    return rsp(results)


def do_jsonreports(request):
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    now = datetime.datetime.utcnow()
    yesterday = dt.dt_to_decimal(yesterday)
    now = dt.dt_to_decimal(now)
    _from = float(request.GET.get('created_from', yesterday))
    _to = float(request.GET.get('created_to', now))
    reports = models.JsonReport.objects.filter(created__gte=_from,
                                               created__lte=_to)
    results = []
    results.append(['Id', 'Start', 'End', 'Created', 'Name', 'Version'])
    for report in reports:
        results.append([report.id,
                        float(dt.dt_to_decimal(report.period_start)),
                        float(dt.dt_to_decimal(report.period_end)),
                        float(report.created),
                        report.name,
                        report.version])
    return rsp(results)


def do_jsonreport(request, report_id):
    report_id = int(report_id)
    report = get_object_or_404(models.JsonReport, pk=report_id)
    return rsp(report.json)
