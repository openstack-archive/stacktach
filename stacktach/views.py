# Copyright 2012 - Dark Secret Software Inc.

import datetime
import json
import pprint

from django import db
from django.shortcuts import render_to_response

from stacktach import datetime_to_decimal as dt
from stacktach import db as stackdb
from stacktach import models
from stacktach import stacklog
from stacktach import utils
from stacktach import notification

STACKDB = stackdb


def log_warn(msg):
    global LOG
    if LOG is None:
        LOG = stacklog.get_logger()
    if LOG is not None:
        LOG.warn(msg)


def start_kpi_tracking(lifecycle, raw):
    """Start the clock for kpi timings when we see an instance.update
    coming in from an api node."""
    if raw.event != "compute.instance.update":
        return

    if "api" not in raw.service:
        return

    tracker = STACKDB.create_request_tracker(request_id=raw.request_id,
                                             start=raw.when,
                                             lifecycle=lifecycle,
                                             last_timing=None,
                                             duration=str(0.0))
    STACKDB.save(tracker)


def update_kpi(timing, raw):
    """Whenever we get a .end event, use the Timing object to
    compute our current end-to-end duration.

    Note: it may not be completely accurate if the operation is
    still in-process, but we have no way of knowing it's still
    in-process without mapping the original command with the
    expected .end event (that's a whole other thing)

    Until then, we'll take the lazy route and be aware of these
    potential fence-post issues."""
    trackers = STACKDB.find_request_trackers(request_id=raw.request_id)
    if len(trackers) == 0:
        return

    tracker = trackers[0]
    tracker.last_timing = timing
    tracker.duration = timing.end_when - tracker.start
    STACKDB.save(tracker)


def aggregate_lifecycle(raw):
    """Roll up the raw event into a Lifecycle object
    and a bunch of Timing objects.

    We can use this for summarized timing reports.

    Additionally, we can use this processing to give
    us end-to-end user request timings for kpi reports.
    """

    if not raw.instance:
        return

    # While we hope only one lifecycle ever exists it's quite
    # likely we get multiple due to the workers and threads.
    lifecycle = None
    lifecycles = STACKDB.find_lifecycles(instance=raw.instance)
    if len(lifecycles) > 0:
        lifecycle = lifecycles[0]
    if not lifecycle:
        lifecycle = STACKDB.create_lifecycle(instance=raw.instance)
    lifecycle.last_raw = raw
    lifecycle.last_state = raw.state
    lifecycle.last_task_state = raw.old_task
    STACKDB.save(lifecycle)

    event = raw.event
    parts = event.split('.')
    step = parts[-1]
    name = '.'.join(parts[:-1])

    if not step in ['start', 'end']:
        # Perhaps it's an operation initiated in the API?
        start_kpi_tracking(lifecycle, raw)
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
    timings = STACKDB.find_timings(name=name, lifecycle=lifecycle)
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
        timing = STACKDB.create_timing(name=name, lifecycle=lifecycle)

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
            # Looks like a valid pair ...
            update_kpi(timing, raw)
    STACKDB.save(timing)


INSTANCE_EVENT = {
    'create_start': 'compute.instance.create.start',
    'create_end': 'compute.instance.create.end',
    'rebuild_start': 'compute.instance.rebuild.start',
    'rebuild_end': 'compute.instance.rebuild.end',
    'resize_prep_start': 'compute.instance.resize.prep.start',
    'resize_prep_end': 'compute.instance.resize.prep.end',
    'resize_revert_start': 'compute.instance.resize.revert.start',
    'resize_revert_end': 'compute.instance.resize.revert.end',
    'resize_finish_end': 'compute.instance.finish_resize.end',
    'rescue_start': 'compute.instance.rescue.start',
    'rescue_end': 'compute.instance.rescue.end',
    'delete_end': 'compute.instance.delete.end',
    'exists': 'compute.instance.exists',
}


def _process_usage_for_new_launch(raw, notification):
    values = {}
    values['instance'] = notification.instance
    values['request_id'] = notification.request_id

    (usage, new) = STACKDB.get_or_create_instance_usage(**values)

    if raw.event in [INSTANCE_EVENT['create_start'],
                     INSTANCE_EVENT['rebuild_start'],
                     INSTANCE_EVENT['rescue_start']]:
        usage.instance_type_id = notification.instance_type_id

    if raw.event in [INSTANCE_EVENT['rebuild_start'],
                     INSTANCE_EVENT['resize_prep_start'],
                     INSTANCE_EVENT['resize_revert_start'],
                     INSTANCE_EVENT['rescue_start']] and\
            usage.launched_at is None:
        # Grab the launched_at so if this action spans the audit period,
        #     we will have a launch record corresponding to the exists.
        #     We don't want to override a launched_at if it is already set
        #     though, because we may have already received the end event
        usage.launched_at = utils.str_time_to_unix(notification.launched_at)

    usage.tenant = notification.tenant
    usage.rax_options = notification.rax_options
    usage.os_architecture = notification.os_architecture
    usage.os_version = notification.os_version
    usage.os_distro = notification.os_distro
    STACKDB.save(usage)


def _process_usage_for_updates(raw, notification):
    if raw.event == INSTANCE_EVENT['create_end']:
        if notification.message and notification.message != 'Success':
            return

    instance_id = notification.instance
    request_id = notification.request_id
    (usage, new) = STACKDB.get_or_create_instance_usage(instance=instance_id,
                                                        request_id=request_id)

    if raw.event in [INSTANCE_EVENT['create_end'],
                     INSTANCE_EVENT['rebuild_end'],
                     INSTANCE_EVENT['resize_finish_end'],
                     INSTANCE_EVENT['resize_revert_end'],
                     INSTANCE_EVENT['rescue_end']]:
        usage.launched_at = utils.str_time_to_unix(notification.launched_at)

    if raw.event == INSTANCE_EVENT['resize_revert_end']:
        usage.instance_type_id = notification.instance_type_id
    elif raw.event == INSTANCE_EVENT['resize_prep_end']:
        usage.instance_type_id = notification.new_instance_type_id

    usage.tenant = notification.tenant
    usage.rax_options = notification.rax_options
    usage.os_architecture = notification.os_architecture
    usage.os_version = notification.os_version
    usage.os_distro = notification.os_distro

    STACKDB.save(usage)


def _process_delete(raw, notification):
    instance_id = notification.instance
    deleted_at = utils.str_time_to_unix(notification.deleted_at)
    values = {
        'instance': instance_id,
        'deleted_at': deleted_at,
    }
    (delete, new) = STACKDB.get_or_create_instance_delete(**values)
    delete.raw = raw

    launched_at = notification.launched_at
    if launched_at and launched_at != '':
        launched_at = utils.str_time_to_unix(launched_at)
        delete.launched_at = launched_at

    STACKDB.save(delete)


def _process_exists(raw, notification):
    instance_id = notification.instance
    launched_at_str = notification.launched_at
    if launched_at_str is not None and launched_at_str != '':
        launched_at = utils.str_time_to_unix(notification.launched_at)
        launched_range = (launched_at, launched_at+1)
        usage = STACKDB.get_instance_usage(instance=instance_id,
                                           launched_at__range=launched_range)
        values = {}
        values['message_id'] = notification.message_id
        values['instance'] = instance_id
        values['launched_at'] = launched_at
        beginning = utils.str_time_to_unix(notification.audit_period_beginning)
        values['audit_period_beginning'] = beginning
        ending = utils.str_time_to_unix(notification.audit_period_ending)
        values['audit_period_ending'] = ending
        values['instance_type_id'] = notification.instance_type_id
        if usage:
            values['usage'] = usage
        values['raw'] = raw
        values['tenant'] = notification.tenant
        values['rax_options'] = notification.rax_options
        values['os_architecture'] = notification.os_architecture
        values['os_version'] = notification.os_version
        values['os_distro'] = notification.os_distro

        deleted_at = notification.deleted_at
        if deleted_at and deleted_at != '':
            # We only want to pre-populate the 'delete' if we know this is in
            #     fact an exist event for a deleted instance. Otherwise, there
            #     is a chance we may populate it for a previous period's exist.
            filter = {'instance': instance_id,
                      'launched_at__range': launched_range}
            delete = STACKDB.get_instance_delete(**filter)
            deleted_at = utils.str_time_to_unix(deleted_at)
            values['deleted_at'] = deleted_at
            if delete:
                values['delete'] = delete

        exists = STACKDB.create_instance_exists(**values)
        STACKDB.save(exists)
    else:
        stacklog.warn("Ignoring exists without launched_at. RawData(%s)" % raw.id)


def _process_glance_usage(raw, notification):
    notification.save_usage(raw)


def _process_glance_delete(raw, notification):
    notification.save_delete(raw)


def _process_glance_exists(raw, notification):
    notification.save_exists(raw)

USAGE_PROCESS_MAPPING = {
    INSTANCE_EVENT['create_start']: _process_usage_for_new_launch,
    INSTANCE_EVENT['rebuild_start']: _process_usage_for_new_launch,
    INSTANCE_EVENT['resize_prep_start']: _process_usage_for_new_launch,
    INSTANCE_EVENT['resize_revert_start']: _process_usage_for_new_launch,
    INSTANCE_EVENT['rescue_start']: _process_usage_for_new_launch,
    INSTANCE_EVENT['create_end']: _process_usage_for_updates,
    INSTANCE_EVENT['rebuild_end']: _process_usage_for_updates,
    INSTANCE_EVENT['resize_prep_end']: _process_usage_for_updates,
    INSTANCE_EVENT['resize_finish_end']: _process_usage_for_updates,
    INSTANCE_EVENT['resize_revert_end']: _process_usage_for_updates,
    INSTANCE_EVENT['rescue_end']: _process_usage_for_updates,
    INSTANCE_EVENT['delete_end']: _process_delete,
    INSTANCE_EVENT['exists']: _process_exists
}

GLANCE_USAGE_PROCESS_MAPPING = {
    'image.activate': _process_glance_usage,
    'image.delete': _process_glance_delete,
    'image.exists': _process_glance_exists
}


def aggregate_usage(raw, notification):
    if not raw.instance:
        return

    if raw.event in USAGE_PROCESS_MAPPING:
        USAGE_PROCESS_MAPPING[raw.event](raw, notification)


def aggregate_glance_usage(raw, body):
    if raw.event in GLANCE_USAGE_PROCESS_MAPPING.keys():
        GLANCE_USAGE_PROCESS_MAPPING[raw.event](raw, body)


def process_raw_data(deployment, args, json_args, exchange):
    """This is called directly by the worker to add the event to the db."""
    db.reset_queries()

    routing_key, body = args
    notif = notification.notification_factory(body, deployment, routing_key,
                                              json_args, exchange)
    raw = notif.save()
    return raw, notif


def post_process_rawdata(raw, notification):
    aggregate_lifecycle(raw)
    aggregate_usage(raw, notification)


def post_process_glancerawdata(raw, notification):
    aggregate_glance_usage(raw, notification)


def post_process_genericrawdata(raw, notification):
    pass


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
    then = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    thend = dt.dt_to_decimal(then)
    query = models.RawData.objects.select_related().filter(when__gt=thend)
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
    updates = request.POST.get('updates', True)
    count = request.POST.get('count', 20)
    if updates and updates == 'true':
        updates = True
    elif updates and updates == 'false':
        updates = False
    rows = None
    if column != None and value != None:
        rows = models.RawData.objects.select_related()
        if deployment_id and int(deployment_id) != 0:
            rows = rows.filter(deployment=deployment_id)
        rows = rows.filter(**{column: value})
        if not updates:
            rows = rows.exclude(event='compute.instance.update')
        rows = rows.order_by('-when')
        if count != 'All':
            rows = rows[:int(count)]
        _post_process_raw_data(rows)
    c['rows'] = rows
    c['allow_expansion'] = True
    c['show_absolute_time'] = True
    return render_to_response('rows.html', c)
