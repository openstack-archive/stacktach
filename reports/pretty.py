import argparse
import datetime
import json
import sys
import time

import prettytable

sys.path.append("/stacktach")

from stacktach import datetime_to_decimal as dt
from stacktach import image_type
from stacktach import models


def make_report(yesterday=None, start_hour=0, hours=24, percentile=90,
                store=False):
    if not yesterday:
        yesterday = datetime.datetime.utcnow().date() - \
                    datetime.timedelta(days=1)

    rstart = datetime.datetime(year=yesterday.year, month=yesterday.month,
                              day=yesterday.day, hour=start_hour)
    rend = rstart + datetime.timedelta(hours=hours-1, minutes=59, seconds=59)

    dstart = dt.dt_to_decimal(rstart)
    dend = dt.dt_to_decimal(rend)

    codes = {}

    # Get all the instances that have changed in the last N hours ...
    updates = models.RawData.objects.filter(event='compute.instance.update',
                                            when__gt=dstart, when__lte=dend)\
                                    .values('instance').distinct()

    expiry = 60 * 60  # 1 hour
    cmds = ['create', 'rebuild', 'rescue', 'resize', 'snapshot']

    failures = {}
    durations = {}
    attempts = {}

    for uuid_dict in updates:
        uuid = uuid_dict['instance']

        # All the unique Request ID's for this instance during that timespan.
        reqs = models.RawData.objects.filter(instance=uuid,
                                             when__gt=dstart, when__lte=dend) \
                                     .values('request_id').distinct()


        for req_dict in reqs:
            report = False
            req = req_dict['request_id']
            raws = models.RawData.objects.filter(request_id=req)\
                                      .exclude(event='compute.instance.exists')\
                                      .order_by('when')

            start = None
            err = None

            operation = "aux"
            image_type_num = 0

            for raw in raws:
                if not start:
                    start = raw.when
                if 'error' in raw.routing_key:
                    err = raw
                    report = True

                for cmd in cmds:
                    if cmd in raw.event:
                        operation = cmd
                        break

                if raw.image_type:
                    image_type_num |= raw.image_type

            image = "?"
            if image_type.isset(image_type_num, image_type.BASE_IMAGE):
                image = "base"
            if image_type.isset(image_type_num, image_type.SNAPSHOT_IMAGE):
                image = "snap"

            if not start:
                continue

            end = raw.when
            diff = end - start

            if diff > 3600:
                report = True

            key = (operation, image)

            # Track durations for all attempts, good and bad ...
            _durations = durations.get(key, [])
            _durations.append(diff)
            durations[key] = _durations

            attempts[key] = attempts.get(key, 0) + 1

            if report:
                failures[key] = failures.get(key, 0) + 1

    # Summarize the results ...
    report = []
    pct = (float(100 - percentile) / 2.0) / 100.0
    details = {'percentile': percentile, 'pct': pct, 'hours': hours,
                   'start': float(dstart), 'end': float(dend)}
    report.append(details)

    cols = ["Operation", "Image", "Min*", "Max*", "Avg*",
            "Requests", "# Fail", "Fail %"]
    report.append(cols)

    total = 0
    failure_total = 0
    for key, count in attempts.iteritems():
        total += count
        operation, image = key

        failure_count = failures.get(key, 0)
        failure_total += failure_count
        failure_percentage = float(failure_count) / float(count)

        # N-th % of durations ...
        _values = durations[key]
        _values.sort()
        _outliers = int(float(len(_values)) * pct)
        if _outliers > 0:
            before = len(_values)
            _values = _values[_outliers:-_outliers]
        _min = 99999999
        _max = 0
        _total = 0.0
        for value in _values:
            _min = min(_min, value)
            _max = max(_max, value)
            _total += float(value)
        _avg = float(_total) / float(len(_values))
        _fmin = dt.sec_to_str(_min)
        _fmax = dt.sec_to_str(_max)
        _favg = dt.sec_to_str(_avg)

        report.append([operation, image, _fmin, _fmax, _favg, count,
                       failure_count, failure_percentage])

    details['total'] = total
    details['failure_total'] = failure_total
    details['failure_rate'] = (float(failure_total)/float(total)) * 100.0
    return (rstart, rend, report)


def valid_date(date):
    try:
        t = time.strptime(date, "%Y-%m-%d")
        return datetime.datetime(*t[:6])
    except Exception, e:
        raise argparse.ArgumentTypeError(
                                    "'%s' is not in YYYY-MM-DD format." % date)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('StackTach Nova Usage Summary Report')
    parser.add_argument('--utcdate',
            help='Report start date YYYY-MM-DD. Default yesterday midnight.',
            type=valid_date, default=None)
    parser.add_argument('--hours',
            help='Report span in hours. Default: 24', default=24,
            type=int)
    parser.add_argument('--start_hour',
            help='Starting hour 0-23. Default: 0', default=0,
            type=int)
    parser.add_argument('--percentile',
            help='Percentile for timings. Default: 90', default=90,
            type=int)
    parser.add_argument('--store',
            help='Store report in database. Default: False',
            default=False, action="store_true")
    parser.add_argument('--silent',
            help="Do not show summary report. Default: False",
            default=False, action="store_true")
    args = parser.parse_args()

    yesterday = args.utcdate
    percentile = args.percentile
    hours = args.hours
    start_hour = args.start_hour
    store_report = args.store

    start, end, raw_report = make_report(yesterday, start_hour, hours,
                                         percentile, store_report)
    details = raw_report[0]
    pct = details['pct']

    if store_report:
        values = {'json': json.dumps(raw_report),
                  'created': dt.dt_to_decimal(datetime.datetime.utcnow()),
                  'period_start': start,
                  'period_end': end,
                  'version': 1,
                  'name': 'summary report'}
        report = models.JsonReport(**values)
        report.save()
        print "Report stored (id=%d)" % report.id

    if args.silent:
        sys.exit(1)

    print "Report for %s to %s" % (start, end)

    cols = raw_report[1]

    # Print the results ...
    p = prettytable.PrettyTable(cols)
    for c in cols[2:]:
        p.align[c] = 'r'
    p.sortby = cols[0]

    print "* Using %d-th percentile for results (+/-%.1f%% cut)" % \
                                (percentile, pct * 100.0)
    for row in raw_report[2:]:
        frow = row[:]
        frow[-1] = "%.1f%%" % (row[-1] * 100.0)
        p.add_row(frow)
    print p

    total = details['total']
    failure_total = details['failure_total']
    failure_rate = details['failure_rate']
    print "Total: %d, Failures: %d, Failure Rate: %.1f%%" % \
                    (total, failure_total, failure_rate)
