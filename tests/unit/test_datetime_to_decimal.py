import datetime
import decimal
import unittest

import utils
utils.setup_sys_path()
from stacktach import datetime_to_decimal

class DatetimeToDecimalTestCase(unittest.TestCase):

    def test_datetime_to_decimal(self):
        expected_decimal = decimal.Decimal('1356093296.123')
        utc_datetime = datetime.datetime.utcfromtimestamp(expected_decimal)
        actual_decimal = datetime_to_decimal.dt_to_decimal(utc_datetime)
        self.assertEqual(actual_decimal, expected_decimal)

    def test_decimal_to_datetime(self):
        expected_decimal = decimal.Decimal('1356093296.123')
        expected_datetime = datetime.datetime.utcfromtimestamp(expected_decimal)
        actual_datetime = datetime_to_decimal.dt_from_decimal(expected_decimal)
        self.assertEqual(actual_datetime, expected_datetime)
