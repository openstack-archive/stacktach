# Copyright 2012 - Rackspace Inc.

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