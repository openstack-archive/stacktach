import decimal
import datetime
import json

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

import datetime_to_decimal as dt
import models
import utils
from django.core.exceptions import ObjectDoesNotExist, FieldError

SECS_PER_HOUR = 60 * 60
SECS_PER_DAY = SECS_PER_HOUR * 24

DEFAULT_LIMIT = 50
HARD_LIMIT = 1000

UTC_FORMAT = '%Y-%m-%d %H:%M:%S'


def _get_limit(request):
    limit = request.GET.get('limit', DEFAULT_LIMIT)
    if limit:
        limit = int(limit)
    if limit > HARD_LIMIT:
        limit = HARD_LIMIT
    return limit


def _get_query_range(request):
    limit = _get_limit(request)
    offset = request.GET.get('offset')

    start = None
    if offset:
        start = int(offset)
    else:
        offset = 0

    end = int(offset) + int(limit)
    return start, end


def model_search(request, model, filters,
                 related=False, order_by=None, excludes=None):

    query = model

    if related:
        query = query.select_related()

    if filters:
        query = query.filter(**filters)
    else:
        query = query.all()

    if excludes:
        for exclude in excludes:
            if isinstance(exclude, dict):
                query = query.exclude(**exclude)
            else:
                query = query.exclude(exclude)

    if order_by:
        query = query.order_by(order_by)

    start, end = _get_query_range(request)
    query = query[start:end]
    return query


def _add_when_filters(request, filters):
    when_max = request.GET.get('when_max')
    if when_max:
        filters['when__lte'] = decimal.Decimal(when_max)

    when_min = request.GET.get('when_min')
    if when_min:
        filters['when__gte'] = decimal.Decimal(when_min)


def get_event_names(service='nova'):
    return _model_factory(service).values('event').distinct()


def get_all_event_names():
    services = ['nova', 'glance', 'generic']
    events = []
    for service in services:
        events.extend(get_event_names(service))
    return events

def get_host_names(service):
    # TODO: We need to upgrade to Django 1.4 so we can get tenent id and
    # host and just do distinct on host name.
    # like: values('host', 'tenant_id').distinct('host')
    # This will be more meaningful. Host by itself isn't really.
    return _model_factory(service).values('host').distinct()


def routing_key_type(key):
    if key.endswith('error'):
        return 'E'
    return ' '


def get_deployments():
    return models.Deployment.objects.all().order_by('name')


def get_timings_for_uuid(request, uuid):
    model = models.Lifecycle.objects
    filters = {'instance': uuid}
    lifecycles = model_search(request, model, filters)

    results = [["?", "Event", "Time (secs)"]]
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


def rsp(data, status=200, content_type="application/json"):
    return HttpResponse(data, content_type=content_type, status=status)


def error_response(status, type, message):
    results = [["Error", "Message"], [type, message]]
    return rsp(json.dumps(results), status)


def do_deployments(request):
    deployments = get_deployments()
    results = [["#", "Name"]]
    for deployment in deployments:
        results.append([deployment.id, deployment.name])
    return rsp(json.dumps(results))


def do_events(request):
    service = str(request.GET.get('service', 'all'))
    if service == 'all':
        events = get_all_event_names()
    else:
        events = get_event_names(service=service)
    results = [["Event Name"]]
    for event in events:
        results.append([event['event']])
    return rsp(json.dumps(results))


def do_hosts(request):
    service = str(request.GET.get('service', 'nova'))
    hosts = get_host_names(service)
    results = [["Host Name"]]
    for host in hosts:
        results.append([host['host']])
    return rsp(json.dumps(results))


def do_uuid(request):
    uuid = str(request.GET['uuid'])
    service = str(request.GET.get('service', 'nova'))
    if not utils.is_uuid_like(uuid):
        msg = "%s is not uuid-like" % uuid
        return error_response(400, 'Bad Request', msg)
    model = _model_factory(service)
    result = []
    filters = {}

    if service == 'nova' or service == 'generic':
        filters = {'instance': uuid}
    if service == 'glance':
        filters = {'uuid': uuid}

    _add_when_filters(request, filters)

    related = model_search(request, model, filters,
                           related=True, order_by='when')
    for event in related:
        when = dt.dt_from_decimal(event.when)
        routing_key_status = routing_key_type(event.routing_key)
        result = event.search_results(result, when, routing_key_status)
    return rsp(json.dumps(result))


def do_timings_uuid(request):
    uuid = request.GET['uuid']
    if not utils.is_uuid_like(uuid):
        msg = "%s is not uuid-like" % uuid
        return error_response(400, 'Bad Request', msg)
    results = get_timings_for_uuid(request, uuid)
    return rsp(json.dumps(results))


def do_timings(request):
    name = request.GET['name']
    model = models.Timing.objects

    filters = {
        'name': name
    }

    if request.GET.get('end_when_min') is not None:
        min_when = decimal.Decimal(request.GET['end_when_min'])
        filters['end_when__gte'] = min_when

    if request.GET.get('end_when_max') is not None:
        max_when = decimal.Decimal(request.GET['end_when_max'])
        filters['end_when__lte'] = max_when

    excludes = [Q(start_raw=None) | Q(end_raw=None), ]
    timings = model_search(request, model, filters,
                           excludes=excludes, related=True,
                           order_by='diff')

    results = [[name, "Time"]]
    for t in timings:
        results.append([t.lifecycle.instance, sec_to_time(t.diff)])
    return rsp(json.dumps(results))


def do_summary(request):
    events = get_event_names()
    interesting = []
    for e in events:
        ev = e['event']
        if ev.endswith('.start'):
            interesting.append(ev[:-len('.start')])

    results = [["Event", "N", "Min", "Max", "Avg"]]

    for name in interesting:
        model = models.Timing.objects
        filters = {'name': name}
        excludes = [
            Q(start_raw=None) | Q(end_raw=None),
            {'diff__lt': 0}
        ]
        timings = model_search(request, model, filters,
                               excludes=excludes)
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
                        sec_to_time(_max), sec_to_time(int(total / num))])
    return rsp(json.dumps(results))


def do_request(request):
    request_id = request.GET['request_id']
    if not utils.is_request_id_like(request_id):
        msg = "%s is not request-id-like" % request_id
        return error_response(400, 'Bad Request', msg)

    model = models.RawData.objects
    filters = {'request_id': request_id}
    _add_when_filters(request, filters)
    events = model_search(request, model, filters, order_by='when')
    results = [["#", "?", "When", "Deployment", "Event", "Host",
                "State", "State'", "Task'"]]
    for e in events:
        when = dt.dt_from_decimal(e.when)
        results.append([e.id, routing_key_type(e.routing_key), str(when),
                        e.deployment.name, e.event, e.host, e.state,
                        e.old_state, e.old_task])
    return rsp(json.dumps(results))


def append_nova_raw_attributes(event, results):
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
    return results


def append_glance_raw_attributes(event, results):
    results.append(["Key", "Value"])
    results.append(["#", event.id])
    when = dt.dt_from_decimal(event.when)
    results.append(["When", str(when)])
    results.append(["Deployment", event.deployment.name])
    results.append(["Category", event.routing_key])
    results.append(["Publisher", event.publisher])
    results.append(["Status", event.status])
    results.append(["Event", event.event])
    results.append(["Service", event.service])
    results.append(["Host", event.host])
    results.append(["UUID", event.uuid])
    results.append(["Req ID", event.request_id])
    return results


def append_generic_raw_attributes(event, results):
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
    return results


def _append_raw_attributes(event, results, service):
    if service == 'nova':
        return append_nova_raw_attributes(event, results)
    if service == 'glance':
        return append_glance_raw_attributes(event, results)
    if service == 'generic':
        return append_generic_raw_attributes(event, results)


def do_show(request, event_id):
    service = str(request.GET.get('service', 'nova'))
    event_id = int(event_id)

    results = []
    model = _model_factory(service)
    try:
        event = model.get(id=event_id)
        results = _append_raw_attributes(event, results, service)
        final = [results, ]
        j = json.loads(event.json)
        final.append(json.dumps(j, indent=2))
        final.append(event.uuid)
        return rsp(json.dumps(final))
    except ObjectDoesNotExist:
        return rsp({})


def _model_factory(service):
    if service == 'glance':
        return models.GlanceRawData.objects
    elif service == 'nova':
        return models.RawData.objects
    elif service == 'generic':
        return models.GenericRawData.objects


def do_watch(request, deployment_id):
    service = str(request.GET.get('service', 'nova'))

    model = _model_factory(service)
    deployment_id = int(deployment_id)
    since = request.GET.get('since')
    event_name = request.GET.get('event_name')

    deployment_map = {}
    for d in get_deployments():
        deployment_map[d.id] = d
    events = get_event_names()
    max_event_width = max([len(event['event']) for event in events])

    base_events = model.order_by('when')
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

    results = []

    for raw in events:
        uuid = raw.uuid
        if not uuid:
            uuid = "-"
        typ = routing_key_type(raw.routing_key)
        when = dt.dt_from_decimal(raw.when)
        results.append([raw.id, typ,
                       str(when.date()), str(when.time()),
                       deployment_map[raw.deployment.id].name,
                       raw.event,
                       uuid])
    results_json = json.dumps([c, results, str(dec_now)])

    return rsp(results_json)


def do_kpi(request, tenant_id=None):
    if tenant_id:
        if models.RawData.objects.filter(tenant=tenant_id).count() == 0:
            message = "Could not find raws for tenant %s" % tenant_id
            return error_response(404, 'Not Found', message)

    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    yesterday = dt.dt_to_decimal(yesterday)
    trackers = models.RequestTracker.objects.select_related()\
                                    .exclude(last_timing=None)\
                                    .exclude(start__lt=yesterday)\
                                    .order_by('duration')

    results = [["Event", "Time", "UUID", "Deployment"]]
    for track in trackers:
        end_event = track.last_timing.end_raw
        event = end_event.event[:-len(".end")]
        uuid = track.lifecycle.instance
        if tenant_id is None or (tenant_id == end_event.tenant):
            results.append([event, sec_to_time(track.duration),
                            uuid, end_event.deployment.name])
    return rsp(json.dumps(results))


def do_list_usage_launches(request):

    filter_args = {}
    if 'instance' in request.GET:
        uuid = request.GET['instance']
        if not utils.is_uuid_like(uuid):
            msg = "%s is not uuid-like" % uuid
            return error_response(400, 'Bad Request', msg)
        filter_args['instance'] = uuid

    model = models.InstanceUsage.objects
    if len(filter_args) > 0:
        launches = model_search(request, model, filter_args)
    else:
        launches = model_search(request, model, None)

    results = [["UUID", "Launched At", "Instance Type Id",
                "Instance Flavor Id"]]

    for launch in launches:
        launched = None
        if launch.launched_at:
            launched = str(dt.dt_from_decimal(launch.launched_at))
        results.append([launch.instance, launched, launch.instance_type_id,
                        launch.instance_flavor_id])

    return rsp(json.dumps(results))


def do_list_usage_deletes(request):

    filter_args = {}
    if 'instance' in request.GET:
        uuid = request.GET['instance']
        if not utils.is_uuid_like(uuid):
            msg = "%s is not uuid-like" % uuid
            return error_response(400, 'Bad Request', msg)
        filter_args['instance'] = uuid

    model = models.InstanceDeletes.objects
    if len(filter_args) > 0:
        deletes = model_search(request, model, filter_args)
    else:
        deletes = model_search(request, model, None)

    results = [["UUID", "Launched At", "Deleted At"]]

    for delete in deletes:
        launched = None
        if delete.launched_at:
            launched = str(dt.dt_from_decimal(delete.launched_at))
        deleted = None
        if delete.deleted_at:
            deleted = str(dt.dt_from_decimal(delete.deleted_at))
        results.append([delete.instance, launched, deleted])

    return rsp(json.dumps(results))


def do_list_usage_exists(request):

    filter_args = {}
    if 'instance' in request.GET:
        uuid = request.GET['instance']
        if not utils.is_uuid_like(uuid):
            msg = "%s is not uuid-like" % uuid
            return error_response(400, 'Bad Request', msg)
        filter_args['instance'] = uuid

    model = models.InstanceExists.objects
    if len(filter_args) > 0:
        exists = model_search(request, model, filter_args)
    else:
        exists = model_search(request, model, None)

    results = [["UUID", "Launched At", "Deleted At", "Instance Type Id",
                "Instance Flavor Id", "Message ID", "Status"]]

    for exist in exists:
        launched = None
        if exist.launched_at:
            launched = str(dt.dt_from_decimal(exist.launched_at))
        deleted = None
        if exist.deleted_at:
            deleted = str(dt.dt_from_decimal(exist.deleted_at))
        results.append([exist.instance, launched, deleted,
                        exist.instance_type_id, exist.instance_flavor_id,
                        exist.message_id, exist.status])

    return rsp(json.dumps(results))


def do_jsonreports(request):
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    now = datetime.datetime.utcnow()
    yesterday = dt.dt_to_decimal(yesterday)
    now = dt.dt_to_decimal(now)
    _from = request.GET.get('created_from', yesterday)
    _to = request.GET.get('created_to', now)
    model = models.JsonReport.objects
    filters = {
        'created__gte': _from,
        'created__lte': _to
    }
    reports = model_search(request, model, filters)
    results = [['Id', 'Start', 'End', 'Created', 'Name', 'Version']]
    for report in reports:
        results.append([report.id,
                        float(dt.dt_to_decimal(report.period_start)),
                        float(dt.dt_to_decimal(report.period_end)),
                        float(report.created),
                        report.name,
                        report.version])
    return rsp(json.dumps(results))


def do_jsonreport(request, report_id):
    report_id = int(report_id)
    report = get_object_or_404(models.JsonReport, pk=report_id)
    return rsp(report.json)


def search(request):
    service = str(request.GET.get('service', 'nova'))
    field = request.GET.get('field')
    value = request.GET.get('value')
    model = _model_factory(service)
    filters = {field: value}
    _add_when_filters(request, filters)
    results = []
    try:

        events = model_search(request, model, filters, order_by='-when')
        for event in events:
            when = dt.dt_from_decimal(event.when)
            routing_key_status = routing_key_type(event.routing_key)
            results = event.search_results(results, when, routing_key_status)
        return rsp(json.dumps(results))
    except ObjectDoesNotExist:
        return error_response(404, 'Not Found', ["The requested object does not exist"])
    except FieldError:
        return error_response(400, 'Bad Request', "The requested field '%s' does not exist for the corresponding object.\n"
                    "Note: The field names of database are case-sensitive." % field)


def do_jsonreports_search(request):
    model = models.JsonReport.objects
    filters = {}
    for filter, value in request.GET.iteritems():
        filters[filter + '__exact'] = value
    try:
        reports = model_search(request, model, filters)
    except FieldError:
        args = request.GET.keys()
        args.sort()
        return error_response(
            400, 'Bad Request', "The requested fields do not exist for "
            "the corresponding object: %s. Note: The field names of database "
            "are case-sensitive." % ', '.join(args))

    results = [['Id', 'Start', 'End', 'Created', 'Name', 'Version']]
    for report in reports:
            results.append([report.id,
                            datetime.datetime.strftime(
                                report.period_start, UTC_FORMAT),
                            datetime.datetime.strftime(
                                report.period_end, UTC_FORMAT),
                            datetime.datetime.strftime(
                                dt.dt_from_decimal(report.created),
                                UTC_FORMAT),
                            report.name,
                            report.version])

    return rsp(json.dumps(results))

