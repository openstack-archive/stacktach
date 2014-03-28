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
import datetime
import decimal

from stacktach import datetime_to_decimal
from tests.unit import StacktachBaseTestCase

class DatetimeToDecimalTestCase(StacktachBaseTestCase):

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
