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

import unittest

import mox

from stacktach import utils as stacktach_utils
from utils import INSTANCE_ID_1
from utils import MESSAGE_ID_1
from utils import REQUEST_ID_1


class StacktachUtilsTestCase(unittest.TestCase):
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