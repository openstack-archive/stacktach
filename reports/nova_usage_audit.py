# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import argparse
import datetime
import functools
import json
import sys
import os

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))

import usage_audit

from stacktach.models import InstanceUsage
from stacktach import datetime_to_decimal as dt
from stacktach import models
from stacktach.reconciler import Reconciler
from stacktach import stacklog

OLD_LAUNCHES_QUERY = """
select stacktach_instanceusage.id,
       stacktach_instanceusage.instance,
       stacktach_instanceusage.launched_at from stacktach_instanceusage
    left outer join stacktach_instancedeletes on
        stacktach_instanceusage.instance = stacktach_instancedeletes.instance
    left outer join stacktach_instancereconcile on
        stacktach_instanceusage.instance = stacktach_instancereconcile.instance
        where (
            stacktach_instancereconcile.deleted_at is null and (
                stacktach_instancedeletes.deleted_at is null or
                stacktach_instancedeletes.deleted_at > %s
            )
            or (stacktach_instancereconcile.deleted_at is not null and
                stacktach_instancereconcile.deleted_at > %s)
        ) and stacktach_instanceusage.launched_at < %s;"""

OLD_RECONCILES_QUERY = """
select stacktach_instancereconcile.id,
       stacktach_instancereconcile.instance,
       stacktach_instancereconcile.launched_at from stacktach_instancereconcile
    left outer join stacktach_instancedeletes on
        stacktach_instancereconcile.instance = stacktach_instancedeletes.instance
        where (
            stacktach_instancereconcile.deleted_at is null and (
                stacktach_instancedeletes.deleted_at is null or
                stacktach_instancedeletes.deleted_at > %s
            )
            or (stacktach_instancereconcile.deleted_at is not null and
                stacktach_instancereconcile.deleted_at > %s)
        ) and stacktach_instancereconcile.launched_at < %s;"""

DEFAULT_UMS_OFFSET = 4 * 60 * 60  # 4 Hours

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


def cell_and_compute(instance, launched_at):
    usage = InstanceUsage.find(instance, launched_at)[0]
    deployment = usage.latest_deployment_for_request_id()
    cell = (deployment and deployment.name) or '-'
    compute = usage.host() or '-'
    return cell, compute


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
                    launched_at = dt.dt_from_decimal(expected['launched_at'])
                    msg = "Couldn't find exists for launch (%s, %s)"
                    msg = msg % (instance, launched_at)
                    cell, compute = cell_and_compute(instance, launched_at)
                    fails.append(['Launch', expected['id'], msg,
                                  'Y' if rec else 'N', cell, compute])
        else:
            rec = False
            if reconciler:
                args = (launches[0]['id'], beginning)
                rec = reconciler.missing_exists_for_instance(*args)
            msg = "No exists for instance (%s)" % instance
            launched_at = dt.dt_from_decimal(launches[0]['launched_at'])
            cell, compute = cell_and_compute(instance, launched_at)
            fails.append(['-', msg, 'Y' if rec else 'N',
                          cell, compute])
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

    # NOTE (apmelton)
    # Django's safe substitution doesn't allow dict substitution...
    # Thus, we send it 'beginning' three times...
    old_recs = models.InstanceReconcile.objects\
                     .raw(OLD_RECONCILES_QUERY,
                          [beginning, beginning, beginning])

    for rec in old_recs:
        instance = rec.instance
        l = {'id': rec.id, 'launched_at': rec.launched_at}
        if instance not in old_launches_dict or \
                (old_launches_dict[instance]['launched_at'] <
                 rec.launched_at):
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


def audit_for_period(beginning, ending, ums=False, ums_offset=0):
    beginning_decimal = dt.dt_to_decimal(beginning)
    ending_decimal = dt.dt_to_decimal(ending)

    if ums:
        verifier_audit_func = functools.partial(
            usage_audit._verifier_audit_for_day_ums, ums_offset=ums_offset
        )
    else:
        verifier_audit_func = usage_audit._verifier_audit_for_day

    (verify_summary,
     verify_detail) = verifier_audit_func(beginning_decimal, ending_decimal,
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
        'version': 7,
        'name': 'nova usage audit'
    }

    report = models.JsonReport(**values)
    report.save()


def make_json_report(summary, details):
    report = {
        'summary': summary,
        'exist_fail_headers': ['Exists Row ID', 'Error Description', 'Cell',
                               'Compute'],
        'exist_fails': details['exist_fails'],
        'launch_fail_headers': ['Launch Row ID', 'Error Description',
                                'Reconciled?', 'Cell', 'Compute'],
        'launch_fails': details['launch_fails']
    }
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
    parser.add_argument('--ums',
                        help="Use query to match UMS, "
                             "period length of 'day' required.",
                        action='store_true')
    parser.add_argument('--ums-offset',
                        help="UMS' fencepost offset in seconds. Default: 4 days",
                        type=int,
                        default=DEFAULT_UMS_OFFSET)
    args = parser.parse_args()

    if args.ums and args.period_length != 'day':
        print "UMS query can only be used with period_length of 'day'."
        sys.exit(0)

    stacklog.set_default_logger_name('nova_usage_audit')
    parent_logger = stacklog.get_logger('nova_usage_audit', is_parent=True)
    log_listener = stacklog.LogListener(parent_logger)
    log_listener.start()

    if args.reconcile:
        with open(args.reconciler_config) as f:
            reconciler_config = json.load(f)
            reconciler = Reconciler(reconciler_config)

    if args.utcdatetime is not None:
        time = args.utcdatetime
    else:
        time = datetime.datetime.utcnow()

    start, end = usage_audit.get_previous_period(time, args.period_length)

    summary, details = audit_for_period(start, end, ums=args.ums,
                                        ums_offset=args.ums_offset)

    if not args.store:
        print make_json_report(summary, details)
    else:
        store_results(start, end, summary, details)
