# Copyright (c) 2012 - Rackspace Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import datetime
import decimal
import unittest

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
