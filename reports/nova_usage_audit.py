# Copyright (c) 2013 - Rackspace Inc.
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

import argparse
import datetime
import json
import sys
import os

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))

from django.db.models import F

from stacktach import datetime_to_decimal as dt
from stacktach import models

OLD_LAUNCHES_QUERY = "select * from stacktach_instanceusage " \
                     "where launched_at is not null and " \
                     "launched_at < %s and instance not in " \
                     "(select distinct(instance) " \
                     "from stacktach_instancedeletes where deleted_at < %s)"


def _get_new_launches(beginning, ending):
    filters = {
        'launched_at__gte': beginning,
        'launched_at__lte': ending,
    }
    return models.InstanceUsage.objects.filter(**filters)


def _get_deletes(beginning, ending):
    filters = {
        'deleted_at__gte': beginning,
        'deleted_at__lte': ending,
    }
    return models.InstanceDeletes.objects.filter(**filters)


def _get_exists(beginning, ending):
    filters = {
        'audit_period_beginning': beginning,
        'audit_period_ending__gte': beginning,
        'audit_period_ending__lte': ending,
    }
    return models.InstanceExists.objects.filter(**filters)


def _audit_launches_to_exists(launches, exists):
    fails = []
    for (instance, launches) in launches.items():
        if instance in exists:
            for launch1 in launches:
                found = False
                for launch2 in exists[instance]:
                    if int(launch1['launched_at']) == int(launch2['launched_at']):
                    # HACK (apmelton): Truncate the decimal because we may not
                    #    have the milliseconds.
                        found = True

                if not found:
                    msg = "Couldn't find exists for launch (%s, %s)"
                    msg = msg % (instance, launch1['launched_at'])
                    fails.append(['Launch', launch1['id'], msg])
        else:
            msg = "No exists for instance (%s)" % instance
            fails.append(['Launch', '-', msg])
    return fails


def _status_queries(exists_query):
    verified = exists_query.filter(status=models.InstanceExists.VERIFIED)
    fail = exists_query.filter(status=models.InstanceExists.FAILED)
    pending = exists_query.filter(status=models.InstanceExists.PENDING)
    verifying = exists_query.filter(status=models.InstanceExists.VERIFYING)

    return verified, fail, pending, verifying


def _send_status_queries(exists_query):
    unsent = exists_query.filter(send_status=0)
    success = exists_query.filter(send_status__gte=200,
                                  send_status__lt=300)
    redirect = exists_query.filter(send_status__gte=300,
                                   send_status__lt=400)
    client_error = exists_query.filter(send_status__gte=400,
                                       send_status__lt=500)
    server_error = exists_query.filter(send_status__gte=500,
                                       send_status__lt=600)
    return success, unsent, redirect, client_error, server_error


def _audit_for_exists(exists_query):
    (verified, fail, pending, verifying) = _status_queries(exists_query)

    (success, unsent, redirect,
     client_error, server_error) = _send_status_queries(verified)

    report = {
        'count': exists_query.count(),
        'verified': verified.count(),
        'failed': fail.count(),
        'pending': pending.count(),
        'verifying': verifying.count(),
        'send_status': {
            'success': success.count(),
            'unsent': unsent.count(),
            'redirect': redirect.count(),
            'client_error': client_error.count(),
            'server_error': server_error.count(),
        }
    }

    return report


def _verifier_audit_for_day(beginning, ending):
    summary = {}

    filters = {
        'raw__when__gte': beginning,
        'raw__when__lte': ending,
        'audit_period_ending': F('audit_period_beginning') + (60*60*24)
    }
    periodic_exists = models.InstanceExists.objects.filter(**filters)

    summary['periodic'] = _audit_for_exists(periodic_exists)

    filters = {
        'raw__when__gte': beginning,
        'raw__when__lte': ending,
        'audit_period_ending__lt': F('audit_period_beginning') + (60*60*24)
    }
    instant_exists = models.InstanceExists.objects.filter(**filters)

    summary['instantaneous'] = _audit_for_exists(instant_exists)

    filters = {
        'raw__when__gte': beginning,
        'raw__when__lte': ending,
        'status': models.InstanceExists.FAILED
    }
    failed = models.InstanceExists.objects.filter(**filters)
    detail = []
    for exist in failed:
        detail.append(['Exist', exist.id, exist.fail_reason])
    return summary, detail


def _launch_audit_for_period(beginning, ending):
    launches_dict = {}
    new_launches = _get_new_launches(beginning, ending)
    for launch in new_launches:
        instance = launch.instance
        l = {'id': launch.id, 'launched_at': launch.launched_at}
        if instance in launches_dict:
            launches_dict[instance].append(l)
        else:
            launches_dict[instance] = [l, ]

    old_launches = models.InstanceUsage.objects.raw(OLD_LAUNCHES_QUERY,
                                                    [beginning, beginning])
    old_launches_dict = {}
    for launch in old_launches:
        instance = launch.instance
        l = {'id': launch.id, 'launched_at': launch.launched_at}
        if instance not in old_launches_dict or \
                (old_launches_dict[instance]['launched_at'] <
                 launch.launched_at):
            old_launches_dict[instance] = l

    for instance, launch in old_launches_dict.items():
        if instance in launches_dict:
            launches_dict[instance].append(launch)
        else:
            launches_dict[instance] = [launch, ]

    exists_dict = {}
    exists = _get_exists(beginning, ending)
    for exist in exists:
        instance = exist.instance
        e = {'id': exist.id,
             'launched_at': exist.launched_at,
             'deleted_at': exist.deleted_at}
        if instance in exists_dict:
            exists_dict[instance].append(e)
        else:
            exists_dict[instance] = [e, ]

    launch_to_exists_fails = _audit_launches_to_exists(launches_dict,
                                                       exists_dict)

    return launch_to_exists_fails, new_launches.count(), len(old_launches_dict)


def audit_for_period(beginning, ending):
    beginning_decimal = dt.dt_to_decimal(beginning)
    ending_decimal = dt.dt_to_decimal(ending)

    (verify_summary,
     verify_detail) = _verifier_audit_for_day(beginning_decimal,
                                              ending_decimal)
    detail, new_count, old_count = _launch_audit_for_period(beginning_decimal,
                                                            ending_decimal)

    summary = {
        'verifier': verify_summary,
        'launch_fails': {
            'total_failures': len(detail),
            'new_launches': new_count,
            'old_launches': old_count
        }
    }

    details = {
        'exist_fails': verify_detail,
        'launch_fails': detail,
    }

    return summary, details


def get_previous_period(time, period_length):
    if period_length == 'day':
        last_period = time - datetime.timedelta(days=1)
        start = datetime.datetime(year=last_period.year,
                                  month=last_period.month,
                                  day=last_period.day)
        end = datetime.datetime(year=time.year,
                                month=time.month,
                                day=time.day)
        return start, end
    elif period_length == 'hour':
        last_period = time - datetime.timedelta(hours=1)
        start = datetime.datetime(year=last_period.year,
                                  month=last_period.month,
                                  day=last_period.day,
                                  hour=last_period.hour)
        end = datetime.datetime(year=time.year,
                                month=time.month,
                                day=time.day,
                                hour=time.hour)
        return start, end


def store_results(start, end, summary, details):
    values = {
        'json': make_json_report(summary, details),
        'created': dt.dt_to_decimal(datetime.datetime.utcnow()),
        'period_start': start,
        'period_end': end,
        'version': 2,
        'name': 'nova usage audit'
    }

    report = models.JsonReport(**values)
    report.save()


def make_json_report(summary, details):
    report = [{'summary': summary},
              ['Object', 'ID', 'Error Description']]
    report.extend(details['exist_fails'])
    report.extend(details['launch_fails'])
    return json.dumps(report)


def valid_datetime(d):
    try:
        t = datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
        return t
    except Exception, e:
        raise argparse.ArgumentTypeError(
            "'%s' is not in YYYY-MM-DD HH:MM:SS format." % d)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('StackTach Nova Usage Audit Report')
    parser.add_argument('--period_length',
                        choices=['hour', 'day'], default='day')
    parser.add_argument('--utcdatetime',
                        help="Override the end time used to generate report.",
                        type=valid_datetime, default=None)
    parser.add_argument('--store',
                        help="If set to true, report will be stored. "
                             "Otherwise, it will just be printed",
                        type=bool, default=False)
    args = parser.parse_args()

    if args.utcdatetime is not None:
        time = args.utcdatetime
    else:
        time = datetime.datetime.utcnow()

    start, end = get_previous_period(time, args.period_length)

    summary, details = audit_for_period(start, end)

    if not args.store:
        print make_json_report(summary, details)
    else:
        store_results(start, end, summary, details)
