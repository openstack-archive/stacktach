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
import time
import os
import prettytable

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))

from stacktach import datetime_to_decimal as dt
from stacktach import image_type
from stacktach import models


def make_report(yesterday=None, start_hour=0, hours=24, percentile=97,
                store=False, region=None, too_long=1800):
    if not yesterday:
        yesterday = datetime.datetime.utcnow().date() -\
            datetime.timedelta(days=1)

    rstart = datetime.datetime(year=yesterday.year, month=yesterday.month,
                               day=yesterday.day, hour=start_hour)
    rend = rstart + datetime.timedelta(hours=hours-1, minutes=59, seconds=59)

    dstart = dt.dt_to_decimal(rstart)
    dend = dt.dt_to_decimal(rend)

    too_long_col = '> %d' % (too_long / 60)

    cells = []
    regions = []
    if region:
        region = region.upper()
    deployments = models.Deployment.objects.all()
    for deployment in deployments:
        name = deployment.name.upper()
        if not region or region in name:
            regions.append(deployment.id)
            cells.append(deployment.name)

    if not len(regions):
        print "No regions found for '%s'" % region
        sys.exit(1)

    # Get all the instances that have changed in the last N hours ...
    updates = models.RawData.objects.filter(event='compute.instance.update',
                                            when__gt=dstart, when__lte=dend,
                                            deployment__in=regions)\
                                    .values('instance').distinct()

    expiry = 60 * 60  # 1 hour
    cmds = ['create', 'rebuild', 'rescue', 'resize', 'snapshot']

    requests = models.RawData.objects.filter(when__gt=dstart, when__lte=dend)\
                                     .exclude(instance=None,
                                              event='compute.instance.exists')\
                                     .values('request_id', 'instance')\
                                     .distinct()
    inst_recs = {}
    for request in requests:
        uuid = request['instance']
        request_id = request['request_id']
        value = inst_recs.get(uuid, [])
        value.append(request_id)
        inst_recs[uuid] = value

    failures = {}  # { key : {failure_type: count} }
    durations = {}
    attempts = {}

    for uuid_dict in updates:
        uuid = uuid_dict['instance']

        for req in inst_recs.get(uuid, []):
            raws = models.RawData.objects.filter(request_id=req)\
                                      .exclude(event='compute.instance.exists')\
                                      .order_by('when')

            start = None
            err = None
            failure_type = None

            operation = "aux"
            image_type_num = 0

            for raw in raws:
                if not start:
                    start = raw.when

                if 'error' in raw.routing_key:
                    err = raw
                    failure_type = 'http'

                if failure_type != 'state' and raw.old_state != 'error'\
                        and raw.state == 'error':
                    failure_type = 'state'

                if raw.old_state == 'error' and \
                        (not raw.state in ['deleted', 'error']):
                    failure_type = None

                for cmd in cmds:
                    if cmd in raw.event:
                        operation = cmd
                        break

                if raw.image_type:
                    image_type_num |= raw.image_type

            # Get image (base or snapshot) from image_type bit field
            image = "?"
            if image_type.isset(image_type_num, image_type.BASE_IMAGE):
                image = "base"
            if image_type.isset(image_type_num, image_type.SNAPSHOT_IMAGE):
                image = "snap"

            #Get os_type from image_type bit field
            os_type = "?"
            if image_type.isset(image_type_num, image_type.LINUX_IMAGE):
                os_type = "linux"
            if image_type.isset(image_type_num, image_type.WINDOWS_IMAGE):
                os_type = "windows"

            if not start:
                continue

            end = raw.when
            diff = end - start

            if diff > too_long and failure_type is None:
                failure_type = too_long_col

            key = (operation, image, os_type)

            # Track durations for all attempts, good and bad ...
            _durations = durations.get(key, [])
            _durations.append(diff)
            durations[key] = _durations

            attempts[key] = attempts.get(key, 0) + 1

            if failure_type:
                if err:
                    queue, body = json.loads(err.json)
                    payload = body['payload']
                    exc = payload.get('exception')
                    if exc:
                        code = int(exc.get('kwargs', {}).get('code', 0))
                        if code >= 400 and code < 500:
                            failure_type = "4xx"
                        if code >= 500 and code < 600:
                            failure_type = "5xx"
                breakdown = failures.get(key, {})
                breakdown[failure_type] = breakdown.get(failure_type, 0) + 1
                failures[key] = breakdown

    # Summarize the results ...
    report = []
    pct = (float(100 - percentile) / 2.0) / 100.0
    details = {'percentile': percentile, 'pct': pct, 'hours': hours,
               'start': float(dstart), 'end': float(dend), 'region': region,
               'cells': cells}
    report.append(details)

    failure_types = ["4xx", "5xx", too_long_col, "state"]
    cols = ["Operation", "Image", "OS Type", "Min", "Max", "Med", "%d%%" % percentile,
            "Requests"]
    for failure_type in failure_types:
        cols.append("%s" % failure_type)
        cols.append("%% %s" % failure_type)
    report.append(cols)

    total = 0
    failure_totals = {}
    for key, count in attempts.iteritems():
        total += count
        operation, image, os_type = key

        breakdown = failures.get(key, {})
        this_failure_pair = []
        for failure_type in failure_types:
            # Failure counts for this attempt.
            # Sum for grand totals.
            failure_count = breakdown.get(failure_type, 0)
            failure_totals[failure_type] = \
                failure_totals.get(failure_type, 0) + failure_count

            # Failure percentage for this attempt.
            percentage = float(failure_count) / float(count)
            this_failure_pair.append((failure_count, percentage))

        # N-th % of durations ...
        _values = durations[key]
        _values.sort()
        _min = 99999999
        _max = 0
        _total = 0.0
        for value in _values:
            _min = min(_min, value)
            _max = max(_max, value)
            _total += float(value)
        _num = len(_values)
        _avg = float(_total) / float(_num)
        half = _num / 2
        _median = _values[half]
        _percentile_index = int((float(percentile) / 100.0) * float(_num))
        _percentile = _values[_percentile_index]

        _fmin = dt.sec_to_str(_min)
        _fmax = dt.sec_to_str(_max)
        _favg = dt.sec_to_str(_avg)
        _fmedian = dt.sec_to_str(_median)
        _fpercentile = dt.sec_to_str(_percentile)

        row = [operation, image, os_type, _fmin, _fmax, _fmedian, _fpercentile, count]
        for failure_count, failure_percentage in this_failure_pair:
            row.append(failure_count)
            row.append(failure_percentage)
        report.append(row)

    details['total'] = total
    failure_grand_total = 0
    for failure_type in failure_types:
        failure_total = failure_totals.get(failure_type, 0)
        failure_grand_total += failure_total
        details["%s failure count" % failure_type] = failure_total
        failure_percentage = (float(failure_total)/float(total)) * 100.0
        details["%s failure percentage" % failure_type] = failure_percentage

    details['failure_grand_total'] = failure_grand_total
    details['failure_grand_rate'] = (float(failure_grand_total)/float(total)) * 100.0
    return (rstart, rend, report)


def valid_date(date):
    try:
        t = time.strptime(date, "%Y-%m-%d")
        return datetime.datetime(*t[:6])
    except Exception:
        raise argparse.ArgumentTypeError(
            "'%s' is not in YYYY-MM-DD format." % date)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('StackTach Nova Usage Summary Report')
    parser.add_argument('--utcdate',
            help='Report start date YYYY-MM-DD. Default yesterday midnight.',
            type=valid_date, default=None)
    parser.add_argument('--region',
            help='Report Region. Default is all regions.', default=None)
    parser.add_argument('--hours',
            help='Report span in hours. Default: 24', default=24,
            type=int)
    parser.add_argument('--days_back',
            help='Report start date. N days back from now. Default: 0', default=0,
            type=int)
    parser.add_argument('--hours_back',
            help='Report start date. N hours back from now. Default: 0', default=0,
            type=int)
    parser.add_argument('--start_hour',
            help='Starting hour 0-23. Default: 0', default=0,
            type=int)
    parser.add_argument('--percentile',
            help='Percentile for timings. Default: 97', default=97,
            type=int)
    parser.add_argument('--too_long',
            help='Seconds for an operation to fail. Default: 1800 (30min)', default=1800,
            type=int)
    parser.add_argument('--store',
            help='Store report in database. Default: False',
            default=False, action="store_true")
    parser.add_argument('--silent',
            help="Do not show summary report. Default: False",
            default=False, action="store_true")
    args = parser.parse_args()

    yesterday = args.utcdate
    days_back = args.days_back
    hours_back = args.hours_back
    percentile = args.percentile
    hours = args.hours
    start_hour = args.start_hour
    store_report = args.store
    region = args.region
    too_long = args.too_long

    if (not yesterday) and days_back > 0:
        yesterday = datetime.datetime.utcnow().date() - \
                    datetime.timedelta(days=days_back)
    if (not yesterday) and hours_back > 0:
        yesterday = datetime.datetime.utcnow() - \
                    datetime.timedelta(hours=hours_back)
        yesterday = yesterday.replace(minute=0, second=0, microsecond=0)
        start_hour = yesterday.hour

    start, end, raw_report = make_report(yesterday, start_hour, hours,
                                         percentile, store_report, region,
                                         too_long)
    details = raw_report[0]
    pct = details['pct']

    region_name = "all"
    if region:
        region_name = region

    if store_report:
        values = {'json': json.dumps(raw_report),
                  'created': dt.dt_to_decimal(datetime.datetime.utcnow()),
                  'period_start': start,
                  'period_end': end,
                  'version': 4,
                  'name': 'summary for region: %s' % region_name}
        report = models.JsonReport(**values)
        report.save()
        print "Report stored (id=%d)" % report.id

    if args.silent:
        sys.exit(1)

    print "'%s' Report for %s to %s" % (region_name, start, end)

    cols = raw_report[1]

    # Print the results ...
    p = prettytable.PrettyTable(cols)
    for c in cols[2:]:
        p.align[c] = 'r'
    p.sortby = cols[0]

    for row in raw_report[2:]:
        frow = row[:]
        for col in [9, 11, 13, 15]:
            frow[col] = "%.1f%%" % (row[col] * 100.0)
        p.add_row(frow)
    print p

    total = details['total']
    failure_total = details['failure_grand_total']
    failure_rate = details['failure_grand_rate']
    print "Total: %d, Failures: %d, Failure Rate: %.1f%%" % \
                    (total, failure_total, failure_rate)
