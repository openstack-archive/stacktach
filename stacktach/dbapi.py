import decimal
import json

from django.forms.models import model_to_dict
from django.http import HttpResponse

import datetime_to_decimal
import models


def rsp(data):
    return HttpResponse(json.dumps(data), content_type="application/json")


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


def _convert_model_list(list):
    converted = []
    for item in list:
        dict = model_to_dict(item)
        for key in dict:
            if isinstance(dict[key], decimal.Decimal):
                dict[key] = str(datetime_to_decimal.dt_from_decimal(dict[key]))
        converted.append(dict)
    return converted
