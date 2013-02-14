import decimal
import json

from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

import datetime_to_decimal as dt
import models


def rsp(data):
    return HttpResponse(json.dumps(data), content_type="application/json")


def _get_model_by_id(klass, model_id):
    model = get_object_or_404(klass, id=model_id)
    model_dict = _convert_model(model)
    return model_dict


def list_usage_launches(request):
    filter_args = {}
    if 'instance' in request.GET:
        filter_args['instance'] = request.GET['instance']

    if len(filter_args) > 0:
        objects = models.InstanceUsage.objects.filter(**filter_args)
    else:
        objects = models.InstanceUsage.objects.all()

    dicts = _convert_model_list(objects.order_by("launched_at"))
    return rsp({'launches': dicts})


def get_usage_launch(request, launch_id):
    return rsp({'launch': _get_model_by_id(models.InstanceUsage, launch_id)})


def list_usage_deletes(request):
    filter_args = {}
    if 'instance' in request.GET:
        filter_args['instance'] = request.GET['instance']

    if len(filter_args) > 0:
        objects = models.InstanceDeletes.objects.filter(**filter_args)
    else:
        objects = models.InstanceDeletes.objects.all()

    dicts = _convert_model_list(objects.order_by("launched_at"))
    return rsp({'deletes': dicts})


def get_usage_delete(request, delete_id):
    return rsp({'delete': _get_model_by_id(models.InstanceDeletes, delete_id)})


def list_usage_exists(request):
    filter_args = {}
    if 'instance' in request.GET:
        filter_args['instance'] = request.GET['instance']

    if len(filter_args) > 0:
        objects = models.InstanceExists.objects.filter(**filter_args)
    else:
        objects = models.InstanceExists.objects.all()

    dicts = _convert_model_list(objects.order_by("id"))
    return rsp({'exists': dicts})


def get_usage_exist(request, exist_id):
    return rsp({'exist': _get_model_by_id(models.InstanceExists, exist_id)})


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
