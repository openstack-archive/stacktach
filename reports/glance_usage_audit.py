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
import json
import os
import sys

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))
from django.db.models import F
from reports import usage_audit
from stacktach import models
from stacktach import datetime_to_decimal as dt

OLD_IMAGES_QUERY = """
select * from stacktach_imageusage left join stacktach_imagedeletes
on (stacktach_imageusage.uuid = stacktach_imagedeletes.uuid and
 deleted_at < %s)
 where stacktach_imagedeletes.id IS NULL
 and created_at is not null and created_at < %s;"""


def audit_usages_to_exists(exists, usages):
    # checks if all exists correspond to the given usages
    fails = []
    for (uuid, images) in usages.items():
        if uuid not in exists:
            msg = "No exists for usage (%s)" % uuid
            fails.append(['Usage', images[0]['id'], msg])
    return fails


def _get_new_images(beginning, ending):
    filters = {
        'created_at__gte': beginning,
        'created_at__lte': ending,
    }
    return models.ImageUsage.objects.filter(**filters)


def _get_exists(beginning, ending):
    filters = {
        'audit_period_beginning': beginning,
        'audit_period_ending__gte': beginning,
        'audit_period_ending__lte': ending,
    }
    return models.ImageExists.objects.filter(**filters)


def valid_datetime(d):
    try:
        t = datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
        return t
    except Exception, e:
        raise argparse.ArgumentTypeError(
            "'%s' is not in YYYY-MM-DD HH:MM:SS format." % d)


def audit_for_period(beginning, ending):
    beginning_decimal = dt.dt_to_decimal(beginning)
    ending_decimal = dt.dt_to_decimal(ending)

    (verify_summary,
     verify_detail) = _verifier_audit_for_day(beginning_decimal,
                                                          ending_decimal,
                                                          models.ImageExists)
    detail, new_count, old_count = _image_audit_for_period(beginning_decimal,
                                                            ending_decimal)

    summary = {
        'verifier': verify_summary,
        'image_summary': {
            'new_images': new_count,
            'old_images': old_count,
            'failures': len(detail)
        },
    }

    details = {
        'exist_fails': verify_detail,
        'image_fails': detail,
    }

    return summary, details


def _verifier_audit_for_day(beginning, ending, exists_model):
    summary = {}
    period = 60*60*24-0.000001
    if args.period_length == 'hour':
        period = 60*60-0.000001
    filters = {
        'raw__when__gte': beginning,
        'raw__when__lte': ending,
        'audit_period_ending': F('audit_period_beginning') + period

    }
    exists = exists_model.objects.filter(**filters)
    summary['exists'] = _audit_for_exists(exists)

    filters = {
        'raw__when__gte': beginning,
        'raw__when__lte': ending,
        'status': exists_model.FAILED
    }
    failed = exists_model.objects.filter(**filters)
    detail = []
    for exist in failed:
        detail.append(['Exist', exist.id, exist.fail_reason])
    return summary, detail


def _audit_for_exists(exists_query):
    (verified, reconciled,
     fail, pending, verifying) = usage_audit._status_queries(exists_query)

    (success, unsent, redirect,
     client_error, server_error) = usage_audit._send_status_queries(verified)

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


def _image_audit_for_period(beginning, ending):
    images_dict = {}
    new_images = _get_new_images(beginning, ending)
    for image in new_images:
        uuid = image.uuid
        l = {'id': image.id, 'created_at': image.created_at}
        if uuid in images_dict:
            images_dict[uuid].append(l)
        else:
            images_dict[uuid] = [l, ]
    # Django's safe substitution doesn't allow dict substitution...
    # Thus, we send it 'beginning' two times...
    old_images = models.ImageUsage.objects\
                         .raw(OLD_IMAGES_QUERY,
                              [beginning, beginning])

    old_images_dict = {}
    for image in old_images:
        uuid = image.uuid
        l = {'id': image.id, 'created_at': image.created_at}
        old_images_dict[uuid] = l

    exists_dict = {}
    exists = _get_exists(beginning, ending)
    for exist in exists:
        uuid = exist.uuid
        e = {'id': exist.id,
             'created_at': exist.created_at,
             'deleted_at': exist.deleted_at}
        if uuid in exists_dict:
            exists_dict[uuid].append(e)
        else:
            exists_dict[uuid] = [e, ]

    image_to_exists_fails = audit_usages_to_exists(exists_dict,images_dict)
    return image_to_exists_fails, new_images.count(), len(old_images_dict)


def store_results(start, end, summary, details):
    values = {
        'json': make_json_report(summary, details),
        'created': dt.dt_to_decimal(datetime.datetime.utcnow()),
        'period_start': start,
        'period_end': end,
        'version': 6,
        'name': 'glance usage audit'
    }

    report = models.JsonReport(**values)
    report.save()


def make_json_report(summary, details):
    report = [{'summary': summary},
              ['Object', 'ID', 'Error Description']]
    report.extend(details['exist_fails'])
    report.extend(details['image_fails'])
    return json.dumps(report)



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

    start, end = usage_audit.get_previous_period(time, args.period_length)

    summary, details = audit_for_period(start, end)

    if not args.store:
        print make_json_report(summary, details)
    else:
        store_results(start, end, summary, details)
