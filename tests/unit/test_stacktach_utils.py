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
import mox
import decimal

from stacktach import utils as stacktach_utils
from utils import INSTANCE_ID_1
from utils import MESSAGE_ID_1
from utils import REQUEST_ID_1
from tests.unit import StacktachBaseTestCase


class StacktachUtilsTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_is_uuid_like(self):
        uuid = INSTANCE_ID_1
        self.assertTrue(stacktach_utils.is_uuid_like(uuid))

    def test_is_uuid_like_no_dashes(self):
        uuid = "08f685d963524dbc827196cc54bf14cd"
        self.assertTrue(stacktach_utils.is_uuid_like(uuid))

    def test_is_uuid_like_invalid(self):
        uuid = "$-^&#$"
        self.assertFalse(stacktach_utils.is_uuid_like(uuid))

    def test_is_request_id_like_with_uuid(self):
        uuid = MESSAGE_ID_1
        self.assertTrue(stacktach_utils.is_request_id_like(uuid))

    def test_is_message_id_like_with_req_uuid(self):
        uuid = REQUEST_ID_1
        self.assertTrue(stacktach_utils.is_request_id_like(uuid))

    def test_is_message_id_like_invalid_req(self):
        uuid = "req-$-^&#$"
        self.assertFalse(stacktach_utils.is_request_id_like(uuid))

    def test_is_message_id_like_invalid(self):
        uuid = "$-^&#$"
        self.assertFalse(stacktach_utils.is_request_id_like(uuid))

    def test_str_time_to_unix(self):
        self.assertEqual(
            stacktach_utils.str_time_to_unix("2013-05-15T11:51:11Z"),
            decimal.Decimal('1368618671'))

        self.assertEqual(
            stacktach_utils.str_time_to_unix("2013-05-15T11:51:11.123Z"),
            decimal.Decimal('1368618671.123'))

        self.assertEqual(
            stacktach_utils.str_time_to_unix("2013-05-15T11:51:11"),
            decimal.Decimal('1368618671'))

        self.assertEqual(
            stacktach_utils.str_time_to_unix("2013-05-15T11:51:11.123"),
            decimal.Decimal('1368618671.123'))

        self.assertEqual(
            stacktach_utils.str_time_to_unix("2013-05-15 11:51:11"),
            decimal.Decimal('1368618671'))

        self.assertEqual(
            stacktach_utils.str_time_to_unix("2013-05-15 11:51:11.123"),
            decimal.Decimal('1368618671.123'))

        with self.assertRaises(Exception):
            stacktach_utils.str_time_to_unix("invalid date"),
            decimal.Decimal('1368618671')
