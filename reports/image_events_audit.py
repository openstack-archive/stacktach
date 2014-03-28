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
import sys
import os

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))

from stacktach import datetime_to_decimal as dt
from stacktach import models


def __get_image_activate_count(beginning, ending):
    upload_filters = {
        'when__gte': beginning,
        'when__lte': ending,
        'event': 'image.upload'
    }
    image_upload = models.GlanceRawData.objects.filter(**upload_filters).count()

    activate_filters = {
        'last_raw__when__gte': beginning,
        'last_raw__when__lte': ending
    }
    image_activate = models.ImageUsage.objects.filter(**activate_filters).count()

    delete_exists_filters = {
        'raw__when__gte': beginning,
        'raw__when__lte': ending
    }
    image_delete = models.ImageDeletes.objects.filter(**delete_exists_filters).count()
    image_exists = models.ImageExists.objects.filter(**delete_exists_filters).count()

    exists_verified_filters = {
        'raw__when__gte': beginning,
        'raw__when__lte': ending,
        'status': models.ImageExists.VERIFIED,
        'send_status__gte': 200,
        'send_status__lt': 300
    }
    image_exists_verified = models.ImageExists.objects.filter(**exists_verified_filters).count()

    return {
        'image.upload': image_upload,
        'image.activate': image_activate,
        'image.delete': image_delete,
        'image.exists': image_exists,
        'image.exists.verified': image_exists_verified
    }


def audit_for_period(beginning, ending):
    beginning_decimal = dt.dt_to_decimal(beginning)
    ending_decimal = dt.dt_to_decimal(ending)

    image_event_counts = __get_image_activate_count(beginning_decimal,
                                              ending_decimal)

    return image_event_counts


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


def __make_json_report(report):
    return json.dumps(report)


def __store_results(start, end, report):
    values = {
        'json': __make_json_report(report),
        'created': dt.dt_to_decimal(datetime.datetime.utcnow()),
        'period_start': start,
        'period_end': end,
        'version': 1,
        'name': 'image events audit'
    }

    report = models.JsonReport(**values)
    report.save()


def valid_datetime(d):
    try:
        t = datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
        return t
    except Exception, e:
        raise argparse.ArgumentTypeError(
            "'%s' is not in YYYY-MM-DD HH:MM:SS format." % d)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('StackTach Image Events Audit Report')
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

    event_counts = audit_for_period(start, end)

    if not args.store:
        print event_counts
    else:
        __store_results(start, end, event_counts)
