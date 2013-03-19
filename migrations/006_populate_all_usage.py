# Copyright 2012 - Rackspace Inc.

import datetime
import os
import sys

import multiprocessing

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from django.core.exceptions import MultipleObjectsReturned

from stacktach import models
from stacktach import views

if __name__ != '__main__':
    sys.exit(1)

events = ['compute.instance.create.start',
          'compute.instance.create.end',
          'compute.instance.rebuild.start',
          'compute.instance.rebuild.end',
          'compute.instance.resize.prep.start',
          'compute.instance.resize.prep.end',
          'compute.instance.finish_resize.end',
          'compute.instance.resize.revert.start',
          'compute.instance.resize.revert.end',
          'compute.instance.delete.end']


def usage_already_exists(raw):
    if raw.event == 'compute.instance.delete.end':
        try:
            models.InstanceDeletes.objects.get(raw=raw)
        except models.InstanceDeletes.DoesNotExist:
            return False
        except MultipleObjectsReturned:
            return True
        return True
    else:
        try:
            models.InstanceUsage.objects.get(instance=raw.instance,
                                             request_id=raw.request_id)
        except models.InstanceUsage.DoesNotExist:
            return False
        except MultipleObjectsReturned:
            print raw.instance
            return True
        return True


def populate_usage(raw):
    if not usage_already_exists(raw):
        views.aggregate_usage(raw)


def add_usage_for_instance(raws):
    completed = 0
    for raw in raws:
        populate_usage(raw)
        completed += 1
    return completed


def print_status(event, completed, total):
    out = (event, completed, total - completed)
    print "%s: %s completed, %s remaining" % out


for event in events:
    pool = multiprocessing.Pool(processes=10)
    raws = models.RawData.objects.filter(event=event).order_by('instance')

    count = raws.count()
    completed = 0
    print_status(event, completed, count)

    def callback(result):
        global completed
        completed += result
        if completed % 1000 == 0:
            print_status(event, completed, count)

    current = None
    raws_for_instance = []
    for raw in raws:
        if current is None:
            current = raw.instance

        if raw.instance != current:
            pool.apply_async(add_usage_for_instance,
                             args=(raws_for_instance,),
                             callback=callback)
            current = raw.instance
            raws_for_instance = [raw]
        else:
            raws_for_instance.append(raw)

    pool.close()
    pool.join()
    print_status(event, completed, count)
