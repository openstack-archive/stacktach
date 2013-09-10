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
from reports import usage_audit

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))

from stacktach import datetime_to_decimal as dt
from stacktach import models
from stacktach.reconciler import Reconciler

OLD_LAUNCHES_QUERY = """
select * from stacktach_instanceusage where
    launched_at is not null and
    launched_at < %s and
    instance not in
        (select distinct(instance)
            from stacktach_instancedeletes where
                deleted_at < %s union
        select distinct(instance)
            from stacktach_instancereconcile where
                deleted_at < %s);"""

reconciler = None


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


def _audit_launches_to_exists(launches, exists, beginning):
    fails = []
    for (instance, launches) in launches.items():
        if instance in exists:
            for expected in launches:
                found = False
                for actual in exists[instance]:
                    if int(expected['launched_at']) == \
                            int(actual['launched_at']):
                    # HACK (apmelton): Truncate the decimal because we may not
                    #    have the milliseconds.
                        found = True

                if not found:
                    rec = False
                    if reconciler:
                        args = (expected['id'], beginning)
                        rec = reconciler.missing_exists_for_instance(*args)
                    msg = "Couldn't find exists for launch (%s, %s)"
                    msg = msg % (instance, expected['launched_at'])
                    fails.append(['Launch', expected['id'], msg, 'Y' if rec else 'N'])
        else:
            rec = False
            if reconciler:
                args = (launches[0]['id'], beginning)
                rec = reconciler.missing_exists_for_instance(*args)
            msg = "No exists for instance (%s)" % instance
            fails.append(['Launch', '-', msg, 'Y' if rec else 'N'])
    return fails


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

    # NOTE (apmelton)
    # Django's safe substitution doesn't allow dict substitution...
    # Thus, we send it 'beginning' three times...
    old_launches = models.InstanceUsage.objects\
                         .raw(OLD_LAUNCHES_QUERY,
                              [beginning, beginning, beginning])

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
                                                       exists_dict,
                                                       beginning)
    return launch_to_exists_fails, new_launches.count(), len(old_launches_dict)


def audit_for_period(beginning, ending):
    beginning_decimal = dt.dt_to_decimal(beginning)
    ending_decimal = dt.dt_to_decimal(ending)

    (verify_summary,
     verify_detail) = usage_audit._verifier_audit_for_day(beginning_decimal,
                                                          ending_decimal,
                                                          models.InstanceExists)
    detail, new_count, old_count = _launch_audit_for_period(beginning_decimal,
                                                            ending_decimal)

    summary = {
        'verifier': verify_summary,
        'launch_summary': {
            'new_launches': new_count,
            'old_launches': old_count,
            'failures': len(detail)
        },
    }

    details = {
        'exist_fails': verify_detail,
        'launch_fails': detail,
    }

    return summary, details


def store_results(start, end, summary, details):
    values = {
        'json': make_json_report(summary, details),
        'created': dt.dt_to_decimal(datetime.datetime.utcnow()),
        'period_start': start,
        'period_end': end,
        'version': 4,
        'name': 'nova usage audit'
    }

    report = models.JsonReport(**values)
    report.save()


def make_json_report(summary, details):
    report = [{'summary': summary},
              ['Object', 'ID', 'Error Description', 'Reconciled?']]
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
    parser.add_argument('--reconcile',
                        help="Enabled reconciliation",
                        type=bool, default=False)
    parser.add_argument('--reconciler_config',
                        help="Location of the reconciler config file",
                        type=str,
                        default='/etc/stacktach/reconciler-config.json')
    args = parser.parse_args()

    if args.reconcile:
        with open(args.reconciler_config) as f:
            reconciler_config = json.load(f)
            reconciler = Reconciler(reconciler_config)

    if args.utcdatetime is not None:
        time = args.utcdatetime
    else:
        time = datetime.datetime.utcnow()

    start, end = usage_audit.get_previous_period(time, args.period_length)

    summary, details = audit_for_period(start, end)

    if not args.store:
        print make_json_report(summary, details)
    else:
        store_results(start, end, summary, details)
