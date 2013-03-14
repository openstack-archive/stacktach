# Copyright 2012 - Rackspace Inc.

import datetime
import os
import sys

import multiprocessing

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

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
          'compute.instance.delete.end',
          'compute.instance.exists']


def add_past_usage(pool, raws):
    count = raws.count()
    print "%s events to be processed" % count
    for raw in raws:
        pool.apply_async(views.aggregate_usage, args=(raw,))
    print "completed processing %s events" % count


for event in events:
    pool = multiprocessing.Pool()
    start_raws = models.RawData.objects.filter(event=event)
    add_past_usage(pool, start_raws)
    pool.close()
    pool.join()