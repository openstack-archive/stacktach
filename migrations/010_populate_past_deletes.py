import datetime
import os
import sys

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from django.db.models import Min

from stacktach import models


if __name__ != '__main__':
    sys.exit(1)


def add_past_deletes(start, end):
    exists = models.InstanceExists.objects.select_related()\
                                  .filter(audit_period_beginning=start,
                                          audit_period_ending=end,
                                          deleted_at__isnull=False)
    i = 0
    for exist in exists:
        i += 1
        print i
        if models.InstanceDeletes.objects\
                 .filter(instance=exist.instance).count() == 0:
            # No deletes found for an instance that was deleted.
            values = {'instance': exist.instance,
                      'launched_at': exist.launched_at,
                      'deleted_at': exist.deleted_at,
                      'request_id': 'req-fake-delete'}
            print values
            models.InstanceDeletes(**values).save()


def find_earliest_daily_audit_period_beginning():
    where = 'audit_period_ending = audit_period_beginning + (60*60*24)'
    query = models.InstanceExists.objects.extra(where=[where])\
                                 .aggregate(Min('audit_period_beginning'))

    return query['audit_period_beginning__min']


start = find_earliest_daily_audit_period_beginning()
end = start + (60 * 60 * 24)

add_past_deletes(start, end)
