import calendar
import datetime
import decimal
import time


def dt_to_decimal(utc):
    decimal.getcontext().prec = 30
    return decimal.Decimal(str(calendar.timegm(utc.utctimetuple()))) + \
           (decimal.Decimal(str(utc.microsecond)) /
           decimal.Decimal("1000000.0"))


def dt_from_decimal(dec):
    if dec == None:
        return "n/a"
    integer = int(dec)
    micro = (dec - decimal.Decimal(integer)) * decimal.Decimal(1000000)

    daittyme = datetime.datetime.utcfromtimestamp(integer)
    return daittyme.replace(microsecond=micro)


def sec_to_str(sec):
    sec = int(sec)
    if sec < 60:
        return "%ds" % sec
    minutes = sec / 60
    sec = sec % 60
    if minutes < 60:
        return "%d:%02ds" % (minutes, sec)
    hours = minutes / 60
    minutes = minutes % 60
    return "%02d:%02d:%02d" % (hours, minutes, sec)
