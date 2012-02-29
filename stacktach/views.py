# Copyright 2012 - Dark Secret Software Inc.

from django.shortcuts import render_to_response
from django import http
from django import template
from django.utils.functional import wraps
from django.views.decorators.csrf import csrf_protect

from stacktach import models

import datetime
import json
import logging
import pprint
import random
import sys

logger = logging.getLogger(__name__)

VERSION = 4


class My401(BaseException):
    pass


class HttpResponseUnauthorized(http.HttpResponse):
    status_code = 401


def _monitor_message(routing_key, body):
    event = body['event_type']
    publisher = body['publisher_id']
    parts = publisher.split('.')   
    service = parts[0]
    host = parts[1]
    payload = body['payload']
    request_spec = payload.get('request_spec', None)
    instance = None
    instance = payload.get('instance_id', instance)
    nova_tenant = body.get('_context_project_id', None)
    nova_tenant = payload.get('tenant_id', nova_tenant)
    return dict(host=host, instance=instance, publisher=publisher,
                service=service, event=event, nova_tenant=nova_tenant)
                

def _compute_update_message(routing_key, body):
    publisher = None
    instance = None
    args = body['args']
    host = args['host']
    service = args['service_name']
    event = body['method']
    nova_tenant = args.get('_context_project_id', None)
    return dict(host=host, instance=instance, publisher=publisher,
                service=service, event=event, nova_tenant=nova_tenant)


# routing_key : handler
HANDLERS = {'monitor.info':_monitor_message,
            'monitor.error':_monitor_message,
            '':_compute_update_message}


def _parse(tenant, args, json_args):
    routing_key, body = args
    handler = HANDLERS.get(routing_key, None)
    if handler:
        values = handler(routing_key, body)
        if not values:
            return {}

        values['tenant'] = tenant
        when = body['_context_timestamp']
        when = datetime.datetime.strptime(when, "%Y-%m-%dT%H:%M:%S.%f")
        values['when'] = when
        values['microseconds'] = when.microsecond
        values['routing_key'] = routing_key
        values['json'] = json_args
        record = models.RawData(**values)
        record.save()
        return values
    return {}


def _post_process_raw_data(rows, state, highlight=None):
    for row in rows:
        if "error" in row.routing_key:
            row.is_error = True
        if highlight and row.id == int(highlight):
            row.highlight = True
        row.when += datetime.timedelta(microseconds=row.microseconds)
        novastats = state.tenant.nova_stats_template
        if novastats and row.instance:
            novastats = novastats.replace("[instance]", row.instance)
        row.novastats = novastats
        loggly = state.tenant.loggly_template
        if loggly and row.instance:
            loggly = loggly.replace("[instance]", row.instance)
        row.loggly = loggly


class State(object):
    def __init__(self):
        self.version = VERSION
        self.tenant = None
 
    def __str__(self):
        tenant = "?"
        if self.tenant:
            tenant = "'%s' - %s (%d)" % (self.tenant.project_name,
                                         self.tenant.email, self.tenant.id)
        return "[Version %s, Tenant %s]" % (self.version, tenant)
 

def _reset_state(request):
    state = State()
    request.session['state'] = state
    return state

   
def _get_state(request, tenant_id=None):
    tenant = None
    if tenant_id:
        try:
            tenant = models.Tenant.objects.get(tenant_id=tenant_id)
        except models.Tenant.DoesNotExist:
            raise My401()

    if 'state' in request.session:
        state = request.session['state']
    else:
        state =_reset_state(request)

    if hasattr(state, 'version') and state.version < VERSION:
        state =_reset_state(request)
        
    state.tenant = tenant

    return state


def tenant_check(view):
    @wraps(view)
    def inner(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        # except HttpResponseUnauthorized, e:
        except My401:
            return HttpResponseUnauthorized()
        
    return inner


def _default_context(state):
    context = dict(utc=datetime.datetime.utcnow(), state=state)
    return context

    
def welcome(request):
    state = _reset_state(request)
    return render_to_response('welcome.html', _default_context(state))


@tenant_check
def home(request, tenant_id):
    state = _get_state(request, tenant_id)
    return render_to_response('index.html', _default_context(state)) 


def logout(request):
    del request.session['state']
    return render_to_response('welcome.html', _default_context(None)) 


@csrf_protect
def new_tenant(request):
    state = _get_state(request)
    context = _default_context(state)
    if request.method == 'POST':
        form = models.TenantForm(request.POST)
        if form.is_valid():
            rec = models.Tenant(**form.cleaned_data)
            rec.save()
            _reset_state(request)
            return http.HttpResponseRedirect('/%d' % rec.tenant_id)
    else:
        form = models.TenantForm()
        context['form'] = form
    return render_to_response('new_tenant.html', context,
                              context_instance=template.RequestContext(request))


@tenant_check
def data(request, tenant_id):
    state = _get_state(request, tenant_id)
    raw_args = request.POST.get('args', "{}")
    args = json.loads(raw_args)
    c = _default_context(state)
    fields = _parse(state.tenant, args, raw_args)
    c['cooked_args'] = fields
    return render_to_response('data.html', c)


@tenant_check
def details(request, tenant_id, column, row_id):
    state = _get_state(request, tenant_id)
    c = _default_context(state)
    row = models.RawData.objects.get(pk=row_id)
    value = getattr(row, column)
    rows = models.RawData.objects.filter(tenant=tenant_id)
    if column != 'when':
        rows = rows.filter(**{column:value})
    else:
        value += datetime.timedelta(microseconds=row.microseconds)
        from_time = value - datetime.timedelta(minutes=1)
        to_time = value + datetime.timedelta(minutes=1)
        rows = rows.filter(when__range=(from_time, to_time))
                                  
    rows = rows.order_by('-when', '-microseconds')[:200]
    _post_process_raw_data(rows, state, highlight=row_id)
    c['rows'] = rows
    c['allow_expansion'] = True
    c['show_absolute_time'] = True
    return render_to_response('rows.html', c)


@tenant_check
def expand(request, tenant_id, row_id):
    state = _get_state(request, tenant_id)
    c = _default_context(state)
    row = models.RawData.objects.get(pk=row_id)
    payload = json.loads(row.json)
    pp = pprint.PrettyPrinter()
    c['payload'] = pp.pformat(payload)
    return render_to_response('expand.html', c)


@tenant_check
def host_status(request, tenant_id):
    state = _get_state(request, tenant_id)
    c = _default_context(state)
    hosts = models.RawData.objects.filter(tenant=tenant_id).\
                                   order_by('-when', '-microseconds')[:20]
    _post_process_raw_data(hosts, state)
    c['rows'] = hosts
    return render_to_response('host_status.html', c)


@tenant_check
def search(request, tenant_id):
    state = _get_state(request, tenant_id)
    c = _default_context(state)
    column = request.POST.get('field', None)
    value = request.POST.get('value', None)
    rows = None
    if column != None and value != None:
        rows = models.RawData.objects.filter(tenant=tenant_id).\
               filter(**{column:value}).\
               order_by('-when', '-microseconds')[:200]
        _post_process_raw_data(rows, state)
    c['rows'] = rows
    c['allow_expansion'] = True
    c['show_absolute_time'] = True
    return render_to_response('rows.html', c)
