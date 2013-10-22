import datetime
import uuid

from stacktach import datetime_to_decimal as dt


def str_time_to_unix(when):
    if 'Z' in when:
        when = _try_parse(when, ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"])
    elif 'T' in when:
        when = _try_parse(when, ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"])
    else:
        when = _try_parse(when, ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"])

    return dt.dt_to_decimal(when)


def _try_parse(when, formats):
    last_exception = None
    for format in formats:
        try:
            when = datetime.datetime.strptime(when, format)
            parsed = True
        except Exception, e:
            parsed = False
            last_exception = e
        if parsed:
            return when
    print "Bad DATE ", last_exception


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