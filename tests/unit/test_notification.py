# Copyright (c) 2013 - Rackspace Inc.
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

from stacktach import notification, utils

from stacktach.notification import Notification
from stacktach.notification import GlanceNotification
from stacktach import db
from tests.unit.utils import REQUEST_ID_1
from tests.unit.utils import TIMESTAMP_1
from tests.unit.utils import TENANT_ID_1
from tests.unit.utils import INSTANCE_ID_1


class NovaNotificationTestCase(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_factory_should_return_nova_notification_for_nova_exchange(
            self):
        body = {}
        deployment = "1"
        json = "{}"
        routing_key = "monitor.info"
        self.mox.StubOutWithMock(notification, 'NovaNotification')
        notification.NovaNotification(body, deployment, routing_key, json)

        self.mox.ReplayAll()
        notification.notification_factory(body, deployment, routing_key, json,
                                          'nova')
        self.mox.VerifyAll()

    def test_factory_should_return_glance_notification_for_glance_exchange(
            self):
        body = {}
        deployment = "1"
        json = "{}"
        routing_key = "monitor_glance.info"

        self.mox.StubOutWithMock(notification, 'GlanceNotification')
        notification.GlanceNotification(body, deployment, routing_key, json)

        self.mox.ReplayAll()
        notification.notification_factory(body, deployment, routing_key, json,
                                          'glance')
        self.mox.VerifyAll()

    def test_factory_should_return_notification_for_unknown_exchange(
            self):
        body = {}
        deployment = "1"
        json = "{}"
        routing_key = "unknown.info"

        self.mox.StubOutWithMock(notification, 'Notification')
        notification.Notification(body, deployment, routing_key, json)

        self.mox.ReplayAll()
        notification.notification_factory(body, deployment, routing_key, json,
                                          'unknown_exchange')
        self.mox.VerifyAll()


class GlanceNotificationTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_save_should_persist_glance_rawdata_to_database(self):
        body = {
            "event_type": "image.upload",
            "timestamp": "2013-06-20 17:31:57.939614",
            "publisher_id": "glance-api01-r2961.global.preprod-ord.ohthree.com",
            "payload": {
                "status": "saving",
                "properties": {
                    "image_type": "snapshot",
                    "instance_uuid": INSTANCE_ID_1,
                },
                "owner": TENANT_ID_1,
                "id": "2df2ccf6-bc1b-4853-aab0-25fda346b3bb",
            }
        }
        deployment = "1"
        routing_key = "glance_monitor.info"
        json = '{["routing_key", {%s}]}' % body
        self.mox.StubOutWithMock(db, 'create_glance_rawdata')
        db.create_glance_rawdata(
            deployment="1",
            owner=TENANT_ID_1,
            json=json,
            routing_key=routing_key,
            when=utils.str_time_to_unix("2013-06-20 17:31:57.939614"),
            publisher="glance-api01-r2961.global.preprod-ord.ohthree.com",
            event="image.upload",
            service="glance-api01-r2961",
            host="global.preprod-ord.ohthree.com",
            instance=INSTANCE_ID_1,
            request_id=None,
            image_type=0,
            status="saving",
            uuid="2df2ccf6-bc1b-4853-aab0-25fda346b3bb")

        self.mox.ReplayAll()

        notification = GlanceNotification(body, deployment, routing_key,
                                          json)
        notification.save()
        self.mox.VerifyAll()


class NotificationTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_save_should_persist_generic_rawdata_to_database(self):
        body = {
            "event_type": "image.upload",
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            "timestamp": TIMESTAMP_1,
            "publisher_id": "glance-api01-r2961.global.preprod-ord.ohthree.com",
            "payload": {
                'instance_id': INSTANCE_ID_1,
                "status": "saving",
                "container_format": "ovf",
                "properties": {
                    "image_type": "snapshot",
                },
                "tenant": "5877054",
            }
        }
        deployment = "1"
        routing_key = "generic_monitor.info"
        json = '{["routing_key", {%s}]}' % body
        self.mox.StubOutWithMock(db, 'create_generic_rawdata')
        db.create_generic_rawdata(
            deployment="1",
            tenant=TENANT_ID_1,
            json=json,
            routing_key=routing_key,
            when=utils.str_time_to_unix(TIMESTAMP_1),
            publisher="glance-api01-r2961.global.preprod-ord.ohthree.com",
            event="image.upload",
            service="glance-api01-r2961",
            host="global.preprod-ord.ohthree.com",
            instance=INSTANCE_ID_1,
            request_id=REQUEST_ID_1)

        self.mox.ReplayAll()

        notification = Notification(body, deployment, routing_key, json)
        notification.save()
        self.mox.VerifyAll()
