# Copyright 2012 - Dark Secret Software Inc.

from django.shortcuts import render_to_response
from django import http
from django import template

from stacktach import models
from stacktach import datetime_to_decimal as dt

import datetime
import json
import pprint


def _extract_states(payload):
    return {
        'state' : payload.get('state', ""),
        'old_state' : payload.get('old_state', ""),
        'old_task' : payload.get('old_task_state', "")
    }


def _monitor_message(routing_key, body):
    event = body['event_type']
    publisher = body['publisher_id']
    request_id = body['_context_request_id']
    parts = publisher.split('.')
    service = parts[0]
    if len(parts) > 1:
        host = ".".join(parts[1:])
    else:
        host = None
    #logging.error("publisher=%s, host=%s" % (publisher, host))
    payload = body['payload']
    request_spec = payload.get('request_spec', None)

    # instance UUID's seem to hide in a lot of odd places.
    instance = payload.get('instance_id', None)
    instance = payload.get('instance_uuid', instance)
    if not instance:
        instance = payload.get('exception', {}).get('kwargs', {}).get('uuid')
    if not instance:
        instance = payload.get('instance', {}).get('uuid')

    tenant = body.get('_context_project_id', None)
    tenant = payload.get('tenant_id', tenant)
    resp = dict(host=host, instance=instance, publisher=publisher,
                service=service, event=event, tenant=tenant,
                request_id=request_id)
    resp.update(_extract_states(payload))
    return resp


def _compute_update_message(routing_key, body):
    publisher = None
    instance = None
    args = body['args']
    host = args['host']
    request_id = body['_context_request_id']
    service = args['service_name']
    event = body['method']
    tenant = args.get('_context_project_id', None)
    resp = dict(host=host, instance=instance, publisher=publisher,
                service=service, event=event, tenant=tenant,
                request_id=request_id)
    payload = data.get('payload', {})
    resp.update(_extract_states(payload))
    return resp


# routing_key : handler
HANDLERS = {'monitor.info':_monitor_message,
            'monitor.error':_monitor_message,
            '':_compute_update_message}


def aggregate(raw):
    """Roll up the raw event into a Lifecycle object
    and a bunch of Timing objects.

    We can use this for summarized timing reports.
    """

    if not raw.instance:
        return

    # While we hope only one lifecycle ever exists it's quite
    # likely we get multiple due to the workers and threads.
    lifecycle = None
    lifecycles = models.Lifecycle.objects.filter(instance=raw.instance)
    if len(lifecycles) > 0:
        lifecycle = lifecycles[0]
    if not lifecycle:
        lifecycle = models.Lifecycle(instance=raw.instance)
    lifecycle.last_raw = raw
    lifecycle.last_state = raw.state
    lifecycle.last_task_state = raw.old_task
    lifecycle.save()

    event = raw.event
    parts = event.split('.')
    step = parts[-1]
    name = '.'.join(parts[:-1])

    if not step in ['start', 'end']:
        return

    # We are going to try to track every event pair that comes
    # through, but that's not as easy as it seems since we don't
    # have a unique key for each request (request_id won't work
    # since the call could come multiple times via a retry loop).
    # So, we're just going to look for Timing objects that have
    # start_raw but no end_raw. This could give incorrect data
    # when/if we get two overlapping foo.start calls (which
    # *shouldn't* happen).
    start = step == 'start'
    timing = None
    timings = models.Timing.objects.filter(name=name, lifecycle=lifecycle)
    if not start:
        for t in timings:
            try:
                if t.end_raw == None and t.start_raw != None:
                    timing = t
                    break
            except models.RawData.DoesNotExist:
                # Our raw data was removed.
                pass

    if timing is None:
        timing = models.Timing(name=name, lifecycle=lifecycle)

    if start:
        timing.start_raw = raw
        timing.start_when = raw.when

        # Erase all the other fields which may have been set
        # the first time this operation was performed.
        # For example, a resize that was done 3 times:
        # We'll only record the last one, but track that 3 were done.
        timing.end_raw = None
        timing.end_when = None

        timing.diff_when = None
        timing.diff_ms = 0
    else:
        timing.end_raw = raw
        timing.end_when = raw.when

        # We could have missed start so watch out ...
        if timing.start_when:
            timing.diff = timing.end_when - timing.start_when
    timing.save()


def process_raw_data(deployment, args, json_args):
    """This is called directly by the worker to add the event to the db."""
    routing_key, body = args
    handler = HANDLERS.get(routing_key, None)
    if handler:
        values = handler(routing_key, body)
        if not values:
            return {}

        values['deployment'] = deployment
        try:
            when = body['timestamp']
        except KeyError:
            when = body['_context_timestamp'] # Old way of doing it
        try:
            try:
                when = datetime.datetime.strptime(when, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                # Old way of doing it
                when = datetime.datetime.strptime(when, "%Y-%m-%dT%H:%M:%S.%f")
        except Exception, e:
            pass
        values['when'] = dt.dt_to_decimal(when)
        values['routing_key'] = routing_key
        values['json'] = json_args
        record = models.RawData(**values)
        record.save()

        aggregate(record)
        return record
    return None


def _post_process_raw_data(rows, highlight=None):
    for row in rows:
        if "error" in row.routing_key:
            row.is_error = True
        if highlight and row.id == int(highlight):
            row.highlight = True
        row.fwhen = dt.dt_from_decimal(row.when)


def _default_context(request, deployment_id=0):
    deployment = None
    if 'deployment' in request.session:
        d = request.session['deployment']
        if d.id == deployment_id:
            deployment = d

    if not deployment and deployment_id:
        try:
            deployment = models.Deployment.objects.get(id=deployment_id)
            request.session['deployment'] = deployment
        except models.Deployment.DoesNotExist:
            pass

    context = dict(utc=datetime.datetime.utcnow(),
                   deployment=deployment,
                   deployment_id=deployment_id)
    return context


def welcome(request):
    deployments = models.Deployment.objects.all().order_by('name')
    context = _default_context(request)
    context['deployments'] = deployments
    return render_to_response('welcome.html', context)


def home(request, deployment_id):
    context = _default_context(request, deployment_id)
    return render_to_response('index.html', context)


def details(request, deployment_id, column, row_id):
    deployment_id = int(deployment_id)
    c = _default_context(request, deployment_id)
    row = models.RawData.objects.get(pk=row_id)
    value = getattr(row, column)
    rows = models.RawData.objects.select_related()
    if deployment_id:
        rows = rows.filter(deployment=deployment_id)
    if column != 'when':
        rows = rows.filter(**{column:value})
    else:
        when = dt.dt_from_decimal(value)
        from_time = when - datetime.timedelta(minutes=1)
        to_time = when + datetime.timedelta(minutes=1)
        from_time_dec = dt.dt_to_decimal(from_time)
        to_time_dec = dt.dt_to_decimal(to_time)
        rows = rows.filter(when__range=(from_time_dec, to_time_dec))

    rows = rows.order_by('-when')[:200]
    _post_process_raw_data(rows, highlight=row_id)
    c['rows'] = rows
    c['allow_expansion'] = True
    c['show_absolute_time'] = True
    return render_to_response('rows.html', c)


def expand(request, deployment_id, row_id):
    c = _default_context(request, deployment_id)
    row = models.RawData.objects.get(pk=row_id)
    payload = json.loads(row.json)
    pp = pprint.PrettyPrinter()
    c['payload'] = pp.pformat(payload)
    return render_to_response('expand.html', c)


def latest_raw(request, deployment_id):
    """This is the 2sec ticker that updates the Recent Activity box."""
    deployment_id = int(deployment_id)
    c = _default_context(request, deployment_id)
    query = models.RawData.objects.select_related()
    if deployment_id > 0:
        query = query.filter(deployment=deployment_id)
    rows = query.order_by('-when')[:20]
    _post_process_raw_data(rows)
    c['rows'] = rows
    return render_to_response('host_status.html', c)


def search(request, deployment_id):
    c = _default_context(request, deployment_id)
    column = request.POST.get('field', None)
    value = request.POST.get('value', None)
    rows = None
    if column != None and value != None:
        rows = models.RawData.objects.select_related()
        if deployment_id:
            row = rows.filter(deployment=deployment_id)
        rows = rows.filter(**{column:value}). \
               order_by('-when')[:22]
        _post_process_raw_data(rows)
    c['rows'] = rows
    c['allow_expansion'] = True
    c['show_absolute_time'] = True
    return render_to_response('rows.html', c)
