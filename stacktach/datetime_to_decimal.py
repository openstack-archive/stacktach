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


if __name__ == '__main__':
    now = datetime.datetime.utcnow()
    d = dt_to_decimal(now)
    daittyme = dt_from_decimal(d)
    print repr(now)
    print repr(d)
    print repr(daittyme)
    assert(now == daittyme)
