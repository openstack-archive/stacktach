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
        # Since deletes only have one event, they either exist or they don't
        try:
            models.InstanceDeletes.objects.get(raw=raw)
        except models.InstanceDeletes.DoesNotExist:
            return False
        except MultipleObjectsReturned:
            return True
        return True
    else:
        # All other usage has multiple events, thus they can exist but be
        # incomplete.
        return False


def populate_usage(raw):
    if not usage_already_exists(raw):
        views.aggregate_usage(raw)


def print_status(event, completed, errored, total):
    out = (event, completed, errored, total - (completed + errored))
    print "%s: %s completed, %s errored, %s remaining" % out


for event in events:
    start = datetime.datetime.utcnow()

    raws = models.RawData.objects.filter(event=event)
    total = raws.count()
    completed = 0
    errored = 0

    print_status(event, completed, errored, total)
    update_interval = datetime.timedelta(seconds=30)
    next_update = start + update_interval
    for raw in raws:
        try:
            populate_usage(raw)
            completed += 1
        except Exception:
            errored += 1
            print "Error with raw: %s" % raw.id

        if datetime.datetime.utcnow() < next_update:
            print_status(event, completed, errored, total)
            next_update = datetime.datetime.utcnow() + update_interval

    end = datetime.datetime.utcnow()
    print_status(event, completed, errored, total)
    print "%s took %s" % (event, end - start)
