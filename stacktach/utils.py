import datetime
import uuid

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


def is_uuid_like(val):
    try:
        converted = str(uuid.UUID(val))
        if '-' not in val:
            converted = converted.replace('-', '')
        return converted == val
    except (TypeError, ValueError, AttributeError):
        return False


def is_request_id_like(val):
    if val[0:4] == 'req-':
        val = val[4:]
    return is_uuid_like(val)