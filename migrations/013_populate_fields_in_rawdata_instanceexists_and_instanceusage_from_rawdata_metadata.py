import os
import sys

try:
    import ujson as json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        import json

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

if __name__ != '__main__':
    sys.exit(1)

from stacktach import models
from stacktach.views import NOTIFICATIONS

usage_events = ['compute.instance.create.start',
    'compute.instance.create.end',
    'compute.instance.rebuild.start',
    'compute.instance.rebuild.end',
    'compute.instance.resize.prep.start',
    'compute.instance.resize.prep.end',
    'compute.instance.resize.revert.start',
    'compute.instance.resize.revert.end',
    'compute.instance.finish_resize.end',
    'compute.instance.delete.end']


def _find_latest_usage_related_raw_id_for_request_id(rawdata_all_queryset, request_id):
    rawdata = rawdata_all_queryset.filter(
        request_id=request_id,
        event__in=usage_events).order_by('id')[:1].values('id')
    if rawdata.count() > 0:
        return rawdata[0]['id']
    return None


def _notification(json_message):
    json_dict = json.loads(json_message)
    routing_key = json_dict[0]
    body = json_dict[1]
    notification = NOTIFICATIONS[routing_key](body)
    return notification


def populate_fields():
    rawdata_all_queryset = models.RawData.objects.filter(event__in=usage_events)

    rawdata_all = rawdata_all_queryset.values('json', 'id')
    for rawdata in rawdata_all:
        notification = _notification(rawdata['json'])
        models.RawDataImageMeta.objects.create(
            raw_id=rawdata['id'],
            os_architecture=notification.os_architecture,
            os_distro=notification.os_distro,
            os_version=notification.os_version,
            rax_options=notification.rax_options)
    print "Populated %s records in RawDataImageMeta" % rawdata_all.count()

    rawdata_exists = models.RawData.objects.filter(
        event__in=['compute.instance.exists']).values('id')
    for rawdata_exist in rawdata_exists:
        image_metadata = models.RawDataImageMeta.objects.filter(raw_id=rawdata_exist['id'])[0]
        models.InstanceExists.objects.filter(
            raw_id=rawdata_exist['id']).update(
                os_architecture=image_metadata.os_architecture,
                os_distro=image_metadata.os_distro,
                os_version=image_metadata.os_version,
                rax_options=image_metadata.rax_options)
    print "Populated %s records in InstanceExists" % rawdata_exists.count()

    usages = models.InstanceUsage.objects.all().values('request_id')
    update_count = 0
    for usage in usages:
        raw_id = _find_latest_usage_related_raw_id_for_request_id(rawdata_all_queryset, usage['request_id'])
        if not raw_id:
            print "No Rawdata entry found for a usage related event with request_id %s" % usage['request_id']
            continue
        image_metadata = models.RawDataImageMeta.objects.filter(raw_id=raw_id)[0]
        models.InstanceUsage.objects.filter(
            request_id=usage['request_id']).update(
                os_architecture=image_metadata.os_architecture,
                os_distro=image_metadata.os_distro,
                os_version=image_metadata.os_version,
                rax_options=image_metadata.rax_options)
        update_count += 1
    print "Populated %s records in InstanceUsages" % update_count

populate_fields()
