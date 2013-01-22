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
    integer = int(dec)
    micro = (dec - decimal.Decimal(integer)) * decimal.Decimal(1000000)

    daittyme = datetime.datetime.utcfromtimestamp(integer)
    return daittyme.replace(microsecond=micro)
