import decimal
import functools
import json

from django.db.models import FieldDoesNotExist
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseServerError
from django.shortcuts import get_object_or_404

from stacktach import datetime_to_decimal as dt
from stacktach import models
from stacktach import utils


class APIException(Exception):
    def __init__(self):
        self.status = 500
        self.message = "Internal Server Error"

    def to_dict(self):
        return {'message': self.message,
                'status': self.status}


class BadRequestException(APIException):
    def __init__(self, message="Bad Request"):
        self.status = 400
        self.message = message


def rsp(data):
    return HttpResponse(json.dumps(data), content_type="application/json")


def api_call(func):

    @functools.wraps(func)
    def handled(*args, **kwargs):
        try:
            return rsp(func(*args, **kwargs))
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


@api_call
def list_usage_exists(request):
    objects = get_db_objects(models.InstanceExists, request, 'id')
    dicts = _convert_model_list(objects)
    return {'exists': dicts}


@api_call
def get_usage_exist(request, exist_id):
    return {'exist': _get_model_by_id(models.InstanceExists, exist_id)}


def _get_model_by_id(klass, model_id):
    model = get_object_or_404(klass, id=model_id)
    model_dict = _convert_model(model)
    return model_dict


def _check_has_field(klass, field_name):
    try:
        klass._meta.get_field_by_name(field_name)
    except FieldDoesNotExist:
        msg = "No such field '%s'." % field_name
        raise BadRequestException(msg)


def _get_filter_args(klass, request):
    filter_args = {}
    if 'instance' in request.GET:
        filter_args['instance'] = request.GET['instance']

    for (key, value) in request.GET.items():

            if key.endswith('_min'):
                k = key[0:-4]
                _check_has_field(klass, k)
                try:
                    filter_args['%s__gte' % k] = utils.str_time_to_unix(value)
                except AttributeError:
                    msg = "Range filters must be dates."
                    raise BadRequestException(message=msg)
            elif key.endswith('_max'):
                k = key[0:-4]
                _check_has_field(klass, k)
                try:
                    filter_args['%s__lte' % k] = utils.str_time_to_unix(value)
                except AttributeError:
                    msg = "Range filters must be dates."
                    raise BadRequestException(message=msg)

    return filter_args


def get_db_objects(klass, request, default_order_by, direction='asc'):
    filter_args = _get_filter_args(klass, request)

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
    limit = request.GET.get('limit')
    if offset:
        start = int(offset)
    else:
        start = None
        offset = 0
    if limit:
        end = int(offset) + int(limit)
    else:
        end = None
    return objects.order_by(order_by)[start:end]


def _convert_model(model):
    model_dict = model_to_dict(model)
    for key in model_dict:
        if isinstance(model_dict[key], decimal.Decimal):
            model_dict[key] = str(dt.dt_from_decimal(model_dict[key]))
    return model_dict


def _convert_model_list(model_list):
    converted = []
    for item in model_list:
        converted.append(_convert_model(item))

    return converted
