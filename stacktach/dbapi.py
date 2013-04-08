# Copyright (c) 2012 - Rackspace Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import decimal
import functools
import json

from django.db import transaction
from django.db.models import FieldDoesNotExist
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseNotFound
from django.http import HttpResponseServerError
from django.shortcuts import get_object_or_404

from stacktach import datetime_to_decimal as dt
from stacktach import models
from stacktach import utils


DEFAULT_LIMIT = 50
HARD_LIMIT = 1000


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


def api_call(func):

    @functools.wraps(func)
    def handled(*args, **kwargs):
        try:
            return rsp(func(*args, **kwargs))
        except NotFoundException, e:
            return HttpResponseNotFound(json.dumps(e.to_dict()),
                                        content_type="application/json")
        except BadRequestException, e:
            return HttpResponseBadRequest(json.dumps(e.to_dict()),
                                          content_type="application/json")
        except APIException, e:
            return HttpResponseServerError(json.dumps(e.to_dict()),
                                           content_type="application/json")

    return handled


@api_call
def list_usage_launches(request):
    objects = get_db_objects(models.InstanceUsage, request, 'launched_at')
    dicts = _convert_model_list(objects)
    return {'launches': dicts}


@api_call
def get_usage_launch(request, launch_id):
    return {'launch': _get_model_by_id(models.InstanceUsage, launch_id)}


@api_call
def list_usage_deletes(request):
    objects = get_db_objects(models.InstanceDeletes, request, 'launched_at')
    dicts = _convert_model_list(objects)
    return {'deletes': dicts}


@api_call
def get_usage_delete(request, delete_id):
    return {'delete': _get_model_by_id(models.InstanceDeletes, delete_id)}


def _exists_extra_values(exist):
    values = {'received': str(dt.dt_from_decimal(exist.raw.when))}
    return values


@api_call
def list_usage_exists(request):
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

    objects = get_db_objects(models.InstanceExists, request, 'id',
                             custom_filters=custom_filters)
    dicts = _convert_model_list(objects, _exists_extra_values)
    return {'exists': dicts}


@api_call
def get_usage_exist(request, exist_id):
    return {'exist': _get_model_by_id(models.InstanceExists, exist_id,
                                      _exists_extra_values)}


@api_call
def exists_send_status(request, message_id):
    if request.method != 'PUT':
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


def _exists_send_status_batch(request):

    body = json.loads(request.body)
    if body.get('messages') is not None:
        messages = body['messages']
        with transaction.commit_on_success():
            for msg_id, status in messages.items():
                try:
                    exist = models.InstanceExists.objects\
                                                 .select_for_update()\
                                                 .get(message_id=msg_id)
                    exist.send_status = status
                    exist.save()
                except models.InstanceExists.DoesNotExist:
                    msg = "Could not find Exists record with message_id = '%s'"
                    msg = msg % msg_id
                    raise NotFoundException(message=msg)
                except models.InstanceExists.MultipleObjectsReturned:
                    msg = "Multiple Exists records with message_id = '%s'"
                    msg = msg % msg_id
                    raise APIException(message=msg)
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


def get_db_objects(klass, request, default_order_by, direction='asc',
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

    offset = request.GET.get('offset')
    limit = request.GET.get('limit', DEFAULT_LIMIT)
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
