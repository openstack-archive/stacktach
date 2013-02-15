import datetime

from stacktach import datetime_to_decimal as dt

def str_time_to_unix(when):
    if 'T' in when:
        try:
            # Old way of doing it
            when = datetime.datetime.strptime(when, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            try:
                # Old way of doing it, no millis
                when = datetime.datetime.strptime(when, "%Y-%m-%dT%H:%M:%S")
            except Exception, e:
                print "BAD DATE: ", e
    else:
        try:
            when = datetime.datetime.strptime(when, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            try:
                when = datetime.datetime.strptime(when, "%Y-%m-%d %H:%M:%S")
            except Exception, e:
                print "BAD DATE: ", e

    return dt.dt_to_decimal(when)
