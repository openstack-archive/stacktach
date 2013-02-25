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
    filter_args = _get_filter_args(models.InstanceUsage, request)

    if len(filter_args) > 0:
        objects = models.InstanceUsage.objects.filter(**filter_args)
    else:
        objects = models.InstanceUsage.objects.all()

    dicts = _convert_model_list(objects.order_by("launched_at"))
    return {'launches': dicts}


@api_call
def get_usage_launch(request, launch_id):
    return {'launch': _get_model_by_id(models.InstanceUsage, launch_id)}


@api_call
def list_usage_deletes(request):
    filter_args = _get_filter_args(models.InstanceDeletes, request)

    if len(filter_args) > 0:
        objects = models.InstanceDeletes.objects.filter(**filter_args)
    else:
        objects = models.InstanceDeletes.objects.all()

    dicts = _convert_model_list(objects.order_by("launched_at"))
    return {'deletes': dicts}


@api_call
def get_usage_delete(request, delete_id):
    return {'delete': _get_model_by_id(models.InstanceDeletes, delete_id)}


@api_call
def list_usage_exists(request):
    filter_args = _get_filter_args(models.InstanceExists, request)

    if len(filter_args) > 0:
        objects = models.InstanceExists.objects.filter(**filter_args)
    else:
        objects = models.InstanceExists.objects.all()

    dicts = _convert_model_list(objects.order_by("id"))
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
