# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import decimal
import datetime
import functools
import json
from datetime import datetime

from django.db import transaction
from django.db.models import Count
from django.db.models import FieldDoesNotExist
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseNotFound
from django.http import HttpResponseServerError
from django.shortcuts import get_object_or_404

from stacktach import datetime_to_decimal as dt
from stacktach import models
from stacktach import stacklog
from stacktach import utils

DEFAULT_LIMIT = 50
HARD_LIMIT = 1000
HARD_WHEN_RANGE_LIMIT = 7 * 24 * 60 * 60  # 7 Days


class APIException(Exception):
    def __init__(self, message="Internal Server Error"):
        self.status = 500
        self.message = message

    def to_dict(self):
        return {'message': self.message,
                'status': self.status}


class BadRequestException(APIException):
    def __init__(self, message="Bad Request"):
        self.status = 400
        self.message = message


class NotFoundException(APIException):
    def __init__(self, message="Not Found"):
        self.status = 404
        self.message = message


def rsp(data):
    if data is None:
        return HttpResponse(content_type="application/json")
    return HttpResponse(json.dumps(data), content_type="application/json")


def _log_api_exception(cls, ex, request):
    line1 = "Exception: %s - %s - %s" % (cls.__name__, ex.status, ex.message)
    line2 = "Request: %s - %s" % (request.method, request.path)
    line3 = "Body: %s" % request.body
    msg = "%s\n%s\n%s" % (line1, line2, line3)
    if 400 <= ex.status < 500:
        stacklog.warn(msg)
    else:
        stacklog.error(msg)


def api_call(func):

    @functools.wraps(func)
    def handled(*args, **kwargs):
        try:
            return rsp(func(*args, **kwargs))
        except NotFoundException, e:
            _log_api_exception(NotFoundException, e, args[0])
            return HttpResponseNotFound(json.dumps(e.to_dict()),
                                        content_type="application/json")
        except BadRequestException, e:
            _log_api_exception(BadRequestException, e, args[0])
            return HttpResponseBadRequest(json.dumps(e.to_dict()),
                                          content_type="application/json")
        except APIException, e:
            _log_api_exception(APIException, e, args[0])
            return HttpResponseServerError(json.dumps(e.to_dict()),
                                           content_type="application/json")

    return handled


def _usage_model_factory(service):
    if service == 'nova':
        return {'klass': models.InstanceUsage, 'order_by': 'launched_at'}
    if service == 'glance':
        return {'klass': models.ImageUsage, 'order_by': 'created_at'}


def _exists_model_factory(service):
    if service == 'nova':
        return {'klass': models.InstanceExists, 'order_by': 'id'}
    if service == 'glance':
        return {'klass': models.ImageExists, 'order_by': 'id'}


def _deletes_model_factory(service):
    if service == 'nova':
        return {'klass': models.InstanceDeletes, 'order_by': 'launched_at'}
    if service == 'glance':
        return {'klass': models.ImageDeletes, 'order_by': 'deleted_at'}

@api_call
def list_usage_launches(request):
    return {'launches': list_usage_launches_with_service(request, 'nova')}

@api_call
def list_usage_images(request):
    return { 'images': list_usage_launches_with_service(request, 'glance')}


def list_usage_launches_with_service(request, service):
    model = _usage_model_factory(service)
    objects = get_db_objects(model['klass'], request,
                             model['order_by'])
    dicts = _convert_model_list(objects)
    return dicts


def get_usage_launch_with_service(launch_id, service):
    model = _usage_model_factory(service)
    return {'launch': _get_model_by_id(model['klass'], launch_id)}

@api_call
def get_usage_launch(request, launch_id):
    return get_usage_launch_with_service(launch_id, 'nova')


@api_call
def get_usage_image(request, image_id):
    return get_usage_launch_with_service(image_id, 'glance')


@api_call
def list_usage_deletes(request):
    return list_usage_deletes_with_service(request, 'nova')


@api_call
def list_usage_deletes_glance(request):
    return list_usage_deletes_with_service(request, 'glance')


def list_usage_deletes_with_service(request, service):
    model = _deletes_model_factory(service)
    objects = get_db_objects(model['klass'], request,
                             model['order_by'])
    dicts = _convert_model_list(objects)
    return {'deletes': dicts}


@api_call
def get_usage_delete(request, delete_id):
    model = _deletes_model_factory('nova')
    return {'delete': _get_model_by_id(model['klass'], delete_id)}


@api_call
def get_usage_delete_glance(request, delete_id):
    model = _deletes_model_factory('glance')
    return {'delete': _get_model_by_id(model['klass'], delete_id)}


def _exists_extra_values(exist):
    values = {'received': str(dt.dt_from_decimal(exist.raw.when))}
    return values


@api_call
def list_usage_exists(request):
    return list_usage_exists_with_service(request, 'nova')


@api_call
def list_usage_exists_glance(request):
    return list_usage_exists_with_service(request, 'glance')


def list_usage_exists_with_service(request, service):
    model = _exists_model_factory(service)
    custom_filters = _get_exists_filter_args(request)
    objects = get_db_objects(model['klass'], request, 'id',
                             custom_filters=custom_filters)
    dicts = _convert_model_list(objects, _exists_extra_values)
    return {'exists': dicts}


@api_call
def get_usage_exist(request, exist_id):
    return {'exist': _get_model_by_id(models.InstanceExists, exist_id,
                                      _exists_extra_values)}

@api_call
def get_usage_exist_glance(request, exist_id):
    return {'exist': _get_model_by_id(models.ImageExists, exist_id,
                                      _exists_extra_values)}


@api_call
def get_usage_exist_stats(request):
    return {'stats': _get_exist_stats(request, 'nova')}


@api_call
def get_usage_exist_stats_glance(request):
    return {'stats': _get_exist_stats(request, 'glance')}


def _get_exist_stats(request, service):
    klass = _exists_model_factory(service)['klass']
    exists_filters = _get_exists_filter_args(request)
    filters = _get_filter_args(klass, request,
                               custom_filters=exists_filters)
    for value in exists_filters.values():
        filters.update(value)
    query = klass.objects.filter(**filters)
    values = query.values('status', 'send_status')
    stats = values.annotate(event_count=Count('send_status'))
    return list(stats)

@api_call
def exists_send_status(request, message_id):
    if request.method not in ['PUT', 'POST']:
        raise BadRequestException(message="Invalid method")

    if request.body is None or request.body == '':
        raise BadRequestException(message="Request body required")

    if message_id == 'batch':
        _exists_send_status_batch(request)
    else:
        body = json.loads(request.body)
        if body.get('send_status') is not None:
            send_status = body['send_status']
            try:
                exist = models.InstanceExists.objects\
                                             .select_for_update()\
                                             .get(message_id=message_id)
                exist.send_status = send_status
                exist.save()
            except models.InstanceExists.DoesNotExist:
                msg = "Could not find Exists record with message_id = '%s'"
                msg = msg % message_id
                raise NotFoundException(message=msg)
            except models.InstanceExists.MultipleObjectsReturned:
                msg = "Multiple Exists records with message_id = '%s'"
                msg = msg % message_id
                raise APIException(message=msg)
        else:
            msg = "'send_status' missing from request body"
            raise BadRequestException(message=msg)


def _find_exists_with_message_id(msg_id, exists_model, service):
    if service == 'glance':
        return exists_model.objects.select_for_update().filter(
            message_id=msg_id)
    elif service == 'nova':
        return [models.InstanceExists.objects.select_for_update()
                .get(message_id=msg_id)]


def _ping_processing_with_service(pings, service, version=1):
    exists_model = _exists_model_factory(service)['klass']
    with transaction.commit_on_success():
            for msg_id, status_info in pings.items():
                try:
                    exists = _find_exists_with_message_id(msg_id, exists_model,
                                                          service)
                    for exists in exists:
                        if version == 1:
                            exists.send_status = status_info
                        elif version == 2:
                            exists.send_status = status_info.get("status", 0)
                            exists.event_id = status_info.get("event_id", "")
                        exists.save()
                except exists_model.DoesNotExist:
                    msg = "Could not find Exists record with message_id = '%s' for %s"
                    msg = msg % (msg_id, service)
                    raise NotFoundException(message=msg)
                except exists_model.MultipleObjectsReturned:
                    msg = "Multiple Exists records with message_id = '%s' for %s"
                    msg = msg % (msg_id, service)
                    print msg
                    raise APIException(message=msg)


def _exists_send_status_batch(request):
    body = json.loads(request.body)
    if body.get('messages') is not None:
        messages = body['messages']
        version = body.get('version', 0)
        if version == 0:
            service = 'nova'
            nova_pings = messages
            if nova_pings:
                _ping_processing_with_service(nova_pings, service)
        if version == 1 or version == 2:
            nova_pings = messages.get('nova', {})
            glance_pings = messages.get('glance', {})
            if nova_pings:
                _ping_processing_with_service(nova_pings, 'nova', version)
            if glance_pings:
                _ping_processing_with_service(glance_pings, 'glance', version)
    else:
        msg = "'messages' missing from request body"
        raise BadRequestException(message=msg)


def _get_model_by_id(klass, model_id, extra_values_func=None):
    model = get_object_or_404(klass, id=model_id)
    model_dict = _convert_model(model, extra_values_func)
    return model_dict


def _check_has_field(klass, field_name):
    try:
        klass._meta.get_field_by_name(field_name)
    except FieldDoesNotExist:
        msg = "No such field '%s'." % field_name
        raise BadRequestException(msg)


def _get_exists_filter_args(request):
    try:
        custom_filters = {}
        if 'received_min' in request.GET:
            received_min = request.GET['received_min']
            custom_filters['received_min'] = {}
            custom_filters['received_min']['raw__when__gte'] = \
                utils.str_time_to_unix(received_min)
        if 'received_max' in request.GET:
            received_max = request.GET['received_max']
            custom_filters['received_max'] = {}
            custom_filters['received_max']['raw__when__lte'] = \
                utils.str_time_to_unix(received_max)
    except AttributeError:
        msg = "Range filters must be dates."
        raise BadRequestException(message=msg)
    return custom_filters


def _get_filter_args(klass, request, custom_filters=None):
    filter_args = {}
    if 'instance' in request.GET:
        uuid = request.GET['instance']
        filter_args['instance'] = uuid
        if not utils.is_uuid_like(uuid):
            msg = "%s is not uuid-like" % uuid
            raise BadRequestException(msg)

    for (key, value) in request.GET.items():
            if not custom_filters or key not in custom_filters:
                if key.endswith('_min'):
                    k = key[0:-4]
                    _check_has_field(klass, k)
                    try:
                        filter_args['%s__gte' % k] = \
                            utils.str_time_to_unix(value)
                    except AttributeError:
                        msg = "Range filters must be dates."
                        raise BadRequestException(message=msg)
                elif key.endswith('_max'):
                    k = key[0:-4]
                    _check_has_field(klass, k)
                    try:
                        filter_args['%s__lte' % k] = \
                            utils.str_time_to_unix(value)
                    except AttributeError:
                        msg = "Range filters must be dates."
                        raise BadRequestException(message=msg)

    return filter_args


def get_db_objects(klass, request, default_order_by, direction='desc',
                   custom_filters=None):
    filter_args = _get_filter_args(klass, request,
                                   custom_filters=custom_filters)
    if custom_filters:
        for key in custom_filters:
            filter_args.update(custom_filters[key])

    if len(filter_args) > 0:
        objects = klass.objects.filter(**filter_args)
    else:
        objects = klass.objects.all()

    order_by = request.GET.get('order_by', default_order_by)
    _check_has_field(klass, order_by)

    direction = request.GET.get('direction', direction)
    if direction == 'desc':
        order_by = '-%s' % order_by
    else:
        order_by = '%s' % order_by

    offset = request.GET.get('offset')
    limit = request.GET.get('limit', DEFAULT_LIMIT)

    if limit:
        limit = int(limit)

    if limit > HARD_LIMIT:
        limit = HARD_LIMIT
    if offset:
        start = int(offset)
    else:
        start = None
        offset = 0
    end = int(offset) + int(limit)
    return objects.order_by(order_by)[start:end]


def _convert_model(model, extra_values_func=None):
    model_dict = model_to_dict(model)
    for key in model_dict:
        if isinstance(model_dict[key], decimal.Decimal):
            model_dict[key] = str(dt.dt_from_decimal(model_dict[key]))
    if extra_values_func:
        model_dict.update(extra_values_func(model))
    return model_dict


def _convert_model_list(model_list, extra_values_func=None):
    converted = []
    for item in model_list:
        converted.append(_convert_model(item, extra_values_func))

    return converted


def _rawdata_factory(service):
    if service == "nova":
        rawdata = models.RawData.objects
    elif service == "glance":
        rawdata = models.GlanceRawData.objects
    else:
        raise BadRequestException(message="Invalid service")
    return rawdata


@api_call
def get_event_stats(request):
    try:
        filters = {}

        if 'when_min' in request.GET or 'when_max' in request.GET:
            if not ('when_min' in request.GET and 'when_max' in request.GET):
                msg = "When providing date range filters, " \
                      "a min and max are required."
                raise BadRequestException(message=msg)

            when_min = utils.str_time_to_unix(request.GET['when_min'])
            when_max = utils.str_time_to_unix(request.GET['when_max'])

            if when_max - when_min > HARD_WHEN_RANGE_LIMIT:
                msg = "Date ranges may be no larger than %s seconds"
                raise BadRequestException(message=msg % HARD_WHEN_RANGE_LIMIT)

            filters['when__lte'] = when_max
            filters['when__gte'] = when_min

        service = request.GET.get("service", "nova")
        rawdata = _rawdata_factory(service)
        if filters:
            rawdata = rawdata.filter(**filters)
        events = rawdata.values('event').annotate(event_count=Count('event'))
        events = list(events)

        if 'event' in request.GET:
            event = request.GET['event']
            default = {'event': event, 'event_count': 0}
            events = [x for x in events if x['event'] == event] or [default, ]

        return {'stats': events}
    except (KeyError, TypeError):
        raise BadRequestException(message="Invalid/absent query parameter")
    except (ValueError, AttributeError):
        raise BadRequestException(message="Invalid format for date (Correct "
                                          "format should be %Y-%m-%d %H:%M:%S)")


def repair_stacktach_down(request):
    post_dict = dict((request.POST._iterlists()))
    message_ids = post_dict.get('message_ids')
    service = post_dict.get('service', ['nova'])
    klass = _exists_model_factory(service[0])['klass']
    absent_exists, exists_not_pending = \
        klass.mark_exists_as_sent_unverified(message_ids)
    response_data = {'absent_exists': absent_exists,
                     'exists_not_pending': exists_not_pending}
    response = HttpResponse(json.dumps(response_data),
                            content_type="application/json")
    return response


def _update_tenant_info_cache(tenant_info):
    tenant_id = tenant_info['tenant']
    try:
        tenant = models.TenantInfo.objects\
                                  .select_for_update()\
                                  .get(tenant=tenant_id)
    except models.TenantInfo.DoesNotExist:
        tenant = models.TenantInfo(tenant=tenant_id)
    tenant.name = tenant_info['name']
    tenant.last_updated = datetime.utcnow()
    tenant.save()

    types = set()
    for type_name, type_value in tenant_info['types'].items():
        try:
            tenant_type = models.TenantType.objects\
                                           .get(name=type_name,
                                                value=type_value)
        except models.TenantType.DoesNotExist:
            tenant_type = models.TenantType(name=type_name,
                                            value=type_value)
            tenant_type.save()
        types.add(tenant_type)
    tenant.types = list(types)
    tenant.save()

def _batch_update_tenant_info(info_list):
    tenant_info = dict((str(info['tenant']), info) for info in info_list)
    tenant_ids = set(tenant_info)
    old_tenants = set(t['tenant'] for t in 
                      models.TenantInfo.objects
                               .filter(tenant__in=list(tenant_ids))
                               .values('tenant'))
    new_tenants = []
    now = datetime.utcnow()
    for tenant in (tenant_ids - old_tenants):
        new_tenants.append(models.TenantInfo(tenant=tenant, 
                                             name=tenant_info[tenant]['name'],
                                             last_updated=now))
    if new_tenants:
        models.TenantInfo.objects.bulk_create(new_tenants)
    tenants = models.TenantInfo.objects.filter(tenant__in=list(tenant_ids))
    tenants.update(last_updated=now)

    types = dict(((tt.name,tt.value),tt) for tt in models.TenantType.objects.all())
    TypeXref = models.TenantInfo.types.through

    changed_tenant_dbids = []
    new_type_xrefs = []
    for tenant in tenants:
        info = tenant_info[tenant.tenant]
        new_types = set()
        for type_name, type_value in info['types'].items():
            ttype = types.get((type_name, type_value))
            if ttype is None:
                ttype = models.TenantType(name=type_name,
                                                value=type_value)
                ttype.save()
                types[(type_name,type_value)] = ttype
            new_types.add(ttype)
        cur_types = set(tenant.types.all())
        if new_types != cur_types:
            if cur_types:
                changed_tenant_dbids.append(tenant.id)
            for ttype in new_types:
                new_type_xrefs.append(TypeXref(tenantinfo_id=tenant.id, tenanttype_id=ttype.id))
    TypeXref.objects.filter(tenantinfo_id__in=changed_tenant_dbids).delete()
    TypeXref.objects.bulk_create(new_type_xrefs)


@api_call
def batch_update_tenant_info(request):
    if request.method not in ['PUT', 'POST']:
        raise BadRequestException(message="Invalid method")

    if request.body is None or request.body == '':
        raise BadRequestException(message="Request body required")

    body = json.loads(request.body)
    if body.get('tenants') is not None:
        tenants = body['tenants']
        _batch_update_tenant_info(tenants)
    else:
        msg = "'tenants' missing from request body"
        raise BadRequestException(message=msg)

@api_call
def update_tenant_info(request, tenant_id):
    if request.method not in ['PUT', 'POST']:
        raise BadRequestException(message="Invalid method")

    if request.body is None or request.body == '':
        raise BadRequestException(message="Request body required")

    body = json.loads(request.body)
    if body['tenant'] != tenant_id:
        raise BadRequestException(message="Invalid tenant: %s != %s" % (body['tenant'], tenant_id)) 
    _update_tenant_info_cache(body)
