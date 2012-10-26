import datetime
import json

from django.db.models import Q
from django.http import HttpResponse

import models
import views


SECS_PER_DAY = 60 * 60 * 24


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


def show_timings_for_uuid(uuid):
    lifecycles = models.Lifecycle.objects.filter(instance=uuid)

    results = []
    for lc in lifecycles:
        timings = models.Timing.objects.filter(lifecycle=lc)
        if not timings:
            continue
        this = []
        this.append(["?", "Event", "Time (secs)"])
        for t in timings:
            state = "?"
            if t.start_raw:
                state = 'S'
            if t.end_raw:
                sate = 'E'
            if t.start_raw and t.end_raw:
                state = "."
            this.append([state, t.name, sec_to_time(seconds_from_timing(t))])
        results.append(this)
    return results


def seconds_from_timedelta(days, seconds, usecs):
    us = usecs / 1000000.0
    return (days * SECS_PER_DAY) + seconds + us


def seconds_from_timing(t):
    return seconds_from_timedelta(t.diff_days, t.diff_seconds, t.diff_usecs)


def sec_to_time(fseconds):
    seconds = int(fseconds)
    usec = fseconds - seconds
    days = seconds / (60 * 60 * 24)
    seconds -= (days * (60 * 60 * 24))
    hours = seconds / (60 * 60)
    seconds -= (hours * (60 * 60))
    minutes = seconds / 60
    seconds -= (minutes * 60)
    usec = ('%.2f' % usec).lstrip('0')
    return "%dd %02d:%02d:%02d%s" % (days, hours, minutes, seconds, usec)


def rsp(data):
    return HttpResponse(json.dumps(data))


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
                        filter(instance=uuid).order_by('when', 'microseconds')
    results = []
    results.append(["#", "?", "When", "Deployment", "Event", "Host",
                        "State", "State'", "Task'"])
    for e in related:
        results.append([e.id, routing_key_type(e.routing_key), str(e.when),
                                        e.deployment.name, e.event,
                                        e.host,
                                        e.state, e.old_state, e.old_task])
    return rsp(results)


def do_timings(request, name):
    results = []
    results.append([name, "Time"])
    timings = models.Timing.objects.select_related().filter(name=name) \
                                  .exclude(Q(start_raw=None) | Q(end_raw=None)) \
                                  .order_by('diff_days', 'diff_seconds',
                                            'diff_usecs')

    for t in timings:
        seconds = seconds_from_timing(t)
        results.append([t.lifecycle.instance, sec_to_time(seconds)])
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
                               .exclude(Q(start_raw=None) | Q(end_raw=None))
        if not timings:
            continue

        total, _min, _max = 0.0, None, None
        num = len(timings)
        for t in timings:
            seconds = seconds_from_timing(t)
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
                                   .order_by('when', 'microseconds')
    results = []
    results.append(["#", "?", "When", "Deployment", "Event", "Host",
                        "State", "State'", "Task'"])
    for e in events:
        results.append([e.id, routing_key_type(e.routing_key), str(e.when),
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


def do_watch(request, deployment_id=None, event_name="", since=None):
    deployment_map = {}
    for d in get_deployments():
        deployment_map[d.id] = d
    events = get_event_names()
    max_event_width = max([len(event['event']) for event in events])
    hosts = get_host_names()
    max_host_width = max([len(host['host']) for host in hosts])

    deployment = None

    if deployment_id:
        deployment = models.Deployment.objects.get(id=deployment_id)

    base_events = models.RawData.objects.order_by('-when', '-microseconds')
    if tenant:
        base_events = base_events.filter(deployment=deployment_id)
    if event_name:
        base_events = base_events.filter(event=event_name)
    if since:
        since = datetime.datetime.strptime(since, "%Y-%m-%d %H:%M:%S.%f")
        events = events.filter(when__gt=since)
    events = events[:20]

    c = [10, 1, 10, 20, max_event_width, 36]
    header = ("+%s" * len(c)) + "+"
    splat = header.replace("+", "|")

    results = []
    results.append([''.center(col, '-') for col in c])
    results.append(['#'.center(c[0]), '?',
                   str(event.when.date()).center(c[2]),
                   'Deployment'.center(c[3]),
                   'Event'.center(c[4]),
                   'UUID'.center(c[5])])
    results.append([''.center(col, '-') for col in c])
    last = None
    for event in events:
        uuid = event.instance
        if not uuid:
            uuid = "-"
        typ = routing_key_type(event.routing_key)
        results.append([str(event.id).center(c[0]),
                       typ,
                       str(event.when.time()).center(c[2]),
                       deployment_map[event.deployment.id].name.center(c[3]),
                       event.event.center(c[4]),
                       uuid.center(c[5])])
        last = event.when
    return rsp([results, last])


def do_kpi(request):
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)

    events = models.RawData.objects.exclude(instance=None)  \
                                   .exclude(when__lt=yesterday) \
                                   .filter(Q(event__endswith='.end') |
                                           Q(event="compute.instance.update")) \
                                   .only('event', 'host', 'request_id',
                                           'instance', 'deployment') \
                                   .order_by('when', 'microseconds')

    events = list(events)
    instance_map = {}  # { uuid: [(request_id, start_event, end_event), ...] }

    for e in events:
        if e.event == "compute.instance.update":
            if "api" in e.host:
                activities = instance_map.get(e.instance, [])
                activities.append((e.request_id, e, None))
                instance_map[e.instance] = activities
            continue

        if not e.event.endswith(".end"):
            continue

        activities = instance_map.get(e.instance)
        if not activities:
            # We missed the api start, skip it
            continue

        found = False
        for index, a in enumerate(activities):
            request_id, start_event, end_event = a
            #if end_event is not None:
            #    continue

            if request_id == e.request_id:
                end_event = e
                activities[index] = (request_id, start_event, e)
                found = True
                break

    results = []
    results.append(["Event", "Time", "UUID", "Deployment"])
    for uuid, activities in instance_map.iteritems():
        for request_id, start_event, end_event in activities:
            if not end_event:
                continue
            event = end_event.event[:-len(".end")]
            start = views._make_datetime_from_raw(start_event.when,
                                                  start_event.microseconds)
            end = views._make_datetime_from_raw(end_event.when,
                                                end_event.microseconds)
            diff = end - start
            results.append([event, sec_to_time(seconds_from_timedelta(
                       diff.days, diff.seconds, diff.microseconds)), uuid,
                       end_event.deployment.name])
    return rsp(results)
