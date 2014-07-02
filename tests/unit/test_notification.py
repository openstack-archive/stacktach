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
import json

import mox

from stacktach import notification, stacklog
from stacktach import utils

from stacktach.notification import Notification
from stacktach.notification import NovaNotification
from stacktach.notification import GlanceNotification
from stacktach import db
from stacktach import image_type
from tests.unit import StacktachBaseTestCase
from tests.unit.utils import BANDWIDTH_PUBLIC_OUTBOUND
from tests.unit.utils import REQUEST_ID_1
from tests.unit.utils import DECIMAL_DUMMY_TIME
from tests.unit.utils import DUMMY_TIME
from tests.unit.utils import TIMESTAMP_1
from tests.unit.utils import TENANT_ID_1
from tests.unit.utils import INSTANCE_ID_1
from tests.unit.utils import MESSAGE_ID_1


class NovaNotificationTestCase(StacktachBaseTestCase):

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

    def test_save_should_persist_nova_rawdata_to_database(self):
        body = {
            "event_type": "compute.instance.exists",
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            "timestamp": TIMESTAMP_1,
            "publisher_id": "compute.global.preprod-ord.ohthree.com",
            "payload": {
                'instance_id': INSTANCE_ID_1,
                "status": "saving",
                "container_format": "ovf",
                "properties": {
                    "image_type": "snapshot",
                },
                "tenant": "5877054",
                "old_state": 'old_state',
                "old_task_state": 'old_task',
                "image_meta": {
                    "org.openstack__1__architecture": 'os_arch',
                    "org.openstack__1__os_distro": 'os_distro',
                    "org.openstack__1__os_version": 'os_version',
                    "com.rackspace__1__options": 'rax_opt',
                },
                "state": 'state',
                "new_task_state": 'task',
                "bandwidth": {
                    "private": {"bw_in": 0, "bw_out": 264902},
                    "public": {"bw_in": 0, "bw_out": 1697240969}
                }
            }
        }
        deployment = "1"
        routing_key = "monitor.info"
        json_body = json.dumps([routing_key, body])
        raw = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(db, 'create_nova_rawdata')
        db.create_nova_rawdata(
            deployment="1",
            tenant=TENANT_ID_1,
            json=json_body,
            routing_key=routing_key,
            when=utils.str_time_to_unix(TIMESTAMP_1),
            publisher="compute.global.preprod-ord.ohthree.com",
            event="compute.instance.exists",
            service="compute",
            host="global.preprod-ord.ohthree.com",
            instance=INSTANCE_ID_1,
            request_id=REQUEST_ID_1,
            image_type=image_type.get_numeric_code(body['payload']),
            old_state='old_state',
            old_task='old_task',
            os_architecture='os_arch',
            os_distro='os_distro',
            os_version='os_version',
            rax_options='rax_opt',
            state='state',
            task='task').AndReturn(raw)

        self.mox.ReplayAll()

        notification = NovaNotification(body, deployment, routing_key, json_body)
        self.assertEquals(notification.save(), raw)
        self.mox.VerifyAll()

    def test_bandwidth_public_out_is_read_from_json(self):
        body = {
            "event_type": "compute.instance.exists",
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            "timestamp": TIMESTAMP_1,
            "publisher_id": "compute.global.preprod-ord.ohthree.com",
            "payload": {
                'instance_id': INSTANCE_ID_1,
                "status": "saving",
                "container_format": "ovf",
                "properties": {
                    "image_type": "snapshot",
                },
                "tenant": "5877054",
                "old_state": 'old_state',
                "old_task_state": 'old_task',
                "image_meta": {
                    "org.openstack__1__architecture": 'os_arch',
                    "org.openstack__1__os_distro": 'os_distro',
                    "org.openstack__1__os_version": 'os_version',
                    "com.rackspace__1__options": 'rax_opt',
                },
                "state": 'state',
                "new_task_state": 'task',
                "bandwidth": {
                    "private": {"bw_in": 0, "bw_out": 264902},
                    "public": {"bw_in": 0, "bw_out": BANDWIDTH_PUBLIC_OUTBOUND}
                }
            }
        }
        deployment = "1"
        routing_key = "monitor.info"
        json_body = json.dumps([routing_key, body])
        notification = NovaNotification(body, deployment, routing_key,
                                        json_body)
        self.assertEquals(notification.bandwidth_public_out,
                          BANDWIDTH_PUBLIC_OUTBOUND)

    def test_bandwidth_public_out_is_set_to_0_if_not_found_in_json(self):
        body = {
            "event_type": "compute.instance.exists",
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            "timestamp": TIMESTAMP_1,
            "publisher_id": "compute.global.preprod-ord.ohthree.com",
            "payload": {
                'instance_id': INSTANCE_ID_1,
                "status": "saving",
                "container_format": "ovf",
                "properties": {
                    "image_type": "snapshot",
                },
                "tenant": "5877054",
                "old_state": 'old_state',
                "old_task_state": 'old_task',
                "image_meta": {
                    "org.openstack__1__architecture": 'os_arch',
                    "org.openstack__1__os_distro": 'os_distro',
                    "org.openstack__1__os_version": 'os_version',
                    "com.rackspace__1__options": 'rax_opt',
                },
                "state": 'state',
                "new_task_state": 'task'
            }
        }
        deployment = "1"
        routing_key = "monitor.info"
        json_body = json.dumps([routing_key, body])
        notification = NovaNotification(body, deployment, routing_key,
                                        json_body)
        self.assertEquals(notification.bandwidth_public_out, 0)


    def test_bandwidth_public_out_is_set_to_blank_object_if_none_in_json(self):
        body = {
            "event_type": "compute.instance.exists",
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            "timestamp": TIMESTAMP_1,
            "publisher_id": "compute.global.preprod-ord.ohthree.com",
            "payload": {
                'instance_id': INSTANCE_ID_1,
                "status": "saving",
                "container_format": "ovf",
                "properties": {
                    "image_type": "snapshot",
                },
                "bandwidth": None,
                "tenant": "5877054",
                "old_state": 'old_state',
                "old_task_state": 'old_task',
                "image_meta": {
                    "org.openstack__1__architecture": 'os_arch',
                    "org.openstack__1__os_distro": 'os_distro',
                    "org.openstack__1__os_version": 'os_version',
                    "com.rackspace__1__options": 'rax_opt',
                },
                "state": 'state',
                "new_task_state": 'task'
            }
        }
        deployment = "1"
        routing_key = "monitor.info"
        json_body = json.dumps([routing_key, body])
        notification = NovaNotification(body, deployment, routing_key,
                                        json_body)
        self.assertEquals(notification.bandwidth_public_out, 0)


class GlanceNotificationTestCase(StacktachBaseTestCase):
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
        json_body = json.dumps([routing_key, body])
        raw = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(db, 'create_glance_rawdata')
        db.create_glance_rawdata(
            deployment="1",
            owner=TENANT_ID_1,
            json=json_body,
            routing_key=routing_key,
            when=utils.str_time_to_unix("2013-06-20 17:31:57.939614"),
            publisher="glance-api01-r2961.global.preprod-ord.ohthree.com",
            event="image.upload",
            service="glance-api01-r2961",
            host="global.preprod-ord.ohthree.com",
            instance=INSTANCE_ID_1,
            request_id='',
            image_type=0,
            status="saving",
            uuid="2df2ccf6-bc1b-4853-aab0-25fda346b3bb").AndReturn(raw)

        self.mox.ReplayAll()

        notification = GlanceNotification(body, deployment, routing_key,
                                          json_body)
        self.assertEquals(notification.save(), raw)
        self.mox.VerifyAll()

    def test_save_should_persist_glance_rawdata_erro_payload_to_database(self):
        body = {
            "event_type": "image.upload",
            "timestamp": "2013-06-20 17:31:57.939614",
            "publisher_id": "glance-api01-r2961.global.preprod-ord.ohthree.com",
            "payload": "error_message"
        }
        deployment = "1"
        routing_key = "glance_monitor.error"
        json_body = json.dumps([routing_key, body])
        raw = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(db, 'create_glance_rawdata')
        db.create_glance_rawdata(
            deployment="1",
            owner=None,
            json=json_body,
            routing_key=routing_key,
            when=utils.str_time_to_unix("2013-06-20 17:31:57.939614"),
            publisher="glance-api01-r2961.global.preprod-ord.ohthree.com",
            event="image.upload",
            service="glance-api01-r2961",
            host="global.preprod-ord.ohthree.com",
            instance=None,
            request_id='',
            image_type=None,
            status=None,
            uuid=None).AndReturn(raw)

        self.mox.ReplayAll()

        notification = GlanceNotification(body, deployment, routing_key,
                                          json_body)
        self.assertEquals(notification.save(), raw)
        self.mox.VerifyAll()

    def test_save_usage_should_persist_image_usage(self):
        raw = self.mox.CreateMockAnything()
        size = 123
        uuid = "2df2ccf6-bc1b-4853-aab0-25fda346b3bb"
        body = {
            "event_type": "image.upload",
            "timestamp": "2013-06-20 18:31:57.939614",
            "publisher_id": "glance-api01-r2961.global.preprod-ord.ohthree.com",
            "payload": {
                "created_at": str(DUMMY_TIME),
                "size": size,
                "owner": TENANT_ID_1,
                "id": "2df2ccf6-bc1b-4853-aab0-25fda346b3bb",
            }
        }
        deployment = "1"
        routing_key = "glance_monitor.info"
        json_body = json.dumps([routing_key, body])

        self.mox.StubOutWithMock(db, 'create_image_usage')
        db.create_image_usage(
            created_at=utils.str_time_to_unix(str(DUMMY_TIME)),
            owner=TENANT_ID_1,
            last_raw=raw,
            size=size,
            uuid=uuid).AndReturn(raw)
        self.mox.ReplayAll()

        notification = GlanceNotification(body, deployment, routing_key,
                                          json_body)
        notification.save_usage(raw)
        self.mox.VerifyAll()

    def test_save_delete_should_persist_image_delete(self):
        raw = self.mox.CreateMockAnything()
        uuid = "2df2ccf6-bc1b-4853-aab0-25fda346b3bb"
        deleted_at = "2013-06-20 14:31:57.939614"
        body = {
            "event_type": "image.delete",
            "publisher_id": "glance-api01-r2961.global.preprod-ord.ohthree.com",
            "payload": {
                "id": "2df2ccf6-bc1b-4853-aab0-25fda346b3bb",
                "deleted_at": deleted_at
            }
        }
        deployment = "1"
        routing_key = "glance_monitor.info"
        json_body = json.dumps([routing_key, body])

        self.mox.StubOutWithMock(db, 'create_image_delete')
        db.create_image_delete(
            raw=raw,
            uuid=uuid,
            deleted_at=utils.str_time_to_unix(deleted_at)).AndReturn(raw)
        self.mox.ReplayAll()

        notification = GlanceNotification(body, deployment, routing_key,
                                          json_body)
        notification.save_delete(raw)
        self.mox.VerifyAll()


class NotificationTestCase(StacktachBaseTestCase):
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
            "message_id": MESSAGE_ID_1,
            "payload": {
                'instance_id': INSTANCE_ID_1,
                "status": "saving",
                "container_format": "ovf",
                "tenant": "5877054"
            }
        }
        deployment = "1"
        routing_key = "generic_monitor.info"
        json_body = json.dumps([routing_key, body])
        raw = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(db, 'create_generic_rawdata')
        db.create_generic_rawdata(
            deployment="1",
            tenant=TENANT_ID_1,
            json=json_body,
            routing_key=routing_key,
            when=utils.str_time_to_unix(TIMESTAMP_1),
            publisher="glance-api01-r2961.global.preprod-ord.ohthree.com",
            event="image.upload",
            service="glance-api01-r2961",
            host="global.preprod-ord.ohthree.com",
            instance=INSTANCE_ID_1,
            request_id=REQUEST_ID_1,
            message_id=MESSAGE_ID_1).AndReturn(raw)

        self.mox.ReplayAll()

        notification = Notification(body, deployment, routing_key, json_body)
        self.assertEquals(notification.save(), raw)
        self.mox.VerifyAll()


class GlanceExistsNotificationTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_save_glancerawdata(self):
        raw = self.mox.CreateMockAnything()
        audit_period_beginning = "2013-05-20 17:31:57.939614"
        audit_period_ending = "2013-06-20 17:31:57.939614"
        created_at = "2013-05-20 19:31:57.939614"
        size = 123
        uuid = "2df2ccf6-bc1b-4853-aab0-25fda346b3bb"
        body = {
            "event_type": "image.exists",
            "timestamp": "2013-06-20 18:31:57.939614",
            "publisher_id": "glance-api01-r2961.global.preprod-ord.ohthree.com",
            "payload": {
                "audit_period_beginning": audit_period_beginning,
                "audit_period_ending": audit_period_ending,
                "owner": TENANT_ID_1,
                "images":
                [
                    {
                        "created_at": created_at,
                        "id": uuid,
                        "size": size,
                        "status": "saving",
                        "properties": {"instance_uuid": INSTANCE_ID_1},
                        "deleted_at": None,
                    },
                    {
                        "created_at": str(DUMMY_TIME),
                        "id": uuid,
                        "size": size,
                        "status": "saving",
                        "properties": {"instance_uuid": INSTANCE_ID_1},
                        "deleted_at": None,
                    }
                ]
            }
        }
        deployment = "1"
        routing_key = "glance_monitor.info"
        json_body = json.dumps([routing_key, body])

        self.mox.StubOutWithMock(db, 'create_glance_rawdata')

        db.create_glance_rawdata(
            deployment="1",
            owner="testtenantid1",
            json=json_body,
            routing_key=routing_key,
            when=utils.str_time_to_unix("2013-06-20 18:31:57.939614"),
            publisher="glance-api01-r2961.global.preprod-ord.ohthree.com",
            event="image.exists",
            service="glance-api01-r2961",
            host="global.preprod-ord.ohthree.com",
            instance=None,
            request_id='',
            image_type=0,
            status=None,
            uuid=None).AndReturn(raw)

        self.mox.ReplayAll()

        notification = GlanceNotification(body, deployment, routing_key,
                                          json_body)
        notification.save()
        self.mox.VerifyAll()

    def test_save_image_exists_with_created_at_but_deleted_at_none(self):
        raw = self.mox.CreateMockAnything()
        audit_period_beginning = "2013-05-20 17:31:57.939614"
        audit_period_ending = "2013-06-20 17:31:57.939614"
        created_at = "2013-05-20 19:31:57.939614"
        size = 123
        uuid = "2df2ccf6-bc1b-4853-aab0-25fda346b3bb"
        body = {
            "event_type": "image.exists",
            "timestamp": "2013-06-20 18:31:57.939614",
            "publisher_id": "glance-api01-r2961.global.preprod-ord.ohthree.com",
            "message_id": "d14cfa51-6a0e-4cf8-9130-804738be96d2",
            "payload": {
                "audit_period_beginning": audit_period_beginning,
                "audit_period_ending": audit_period_ending,
                "owner": TENANT_ID_1,
                "images":
                [
                    {
                        "created_at": created_at,
                        "id": uuid,
                        "size": size,
                        "status": "saving",
                        "properties": {"instance_uuid": INSTANCE_ID_1},
                        "deleted_at": None,
                    },
                    {
                        "created_at": created_at,
                        "id": uuid,
                        "size": size,
                        "status": "saving",
                        "properties": {"instance_uuid": INSTANCE_ID_1},
                        "deleted_at": None,
                    }
                ]
            }
        }
        deployment = "1"
        routing_key = "glance_monitor.info"
        json_body = json.dumps([routing_key, body])

        self.mox.StubOutWithMock(db, 'create_image_exists')
        self.mox.StubOutWithMock(db, 'get_image_usage')

        for i in range(0, 2):
            db.get_image_usage(uuid=uuid).AndReturn(None)
            db.create_image_exists(
                created_at=utils.str_time_to_unix(created_at),
                owner=TENANT_ID_1,
                raw=raw,
                audit_period_beginning=utils.str_time_to_unix(audit_period_beginning),
                audit_period_ending=utils.str_time_to_unix(audit_period_ending),
                size=size,
                uuid=uuid,
                usage=None,
                message_id="d14cfa51-6a0e-4cf8-9130-804738be96d2").AndReturn(raw)

        self.mox.ReplayAll()

        notification = GlanceNotification(body, deployment, routing_key,
                                          json_body)
        notification.save_exists(raw)
        self.mox.VerifyAll()

    def test_save_image_exists_with_created_at_and_deleted_at(self):
        raw = self.mox.CreateMockAnything()
        delete = self.mox.CreateMockAnything()
        audit_period_beginning = "2013-05-20 17:31:57.939614"
        audit_period_ending = "2013-06-20 17:31:57.939614"
        created_at = "2013-05-20 19:31:57.939614"
        deleted_at = "2013-05-20 21:31:57.939614"
        size = 123
        uuid = "2df2ccf6-bc1b-4853-aab0-25fda346b3bb"
        body = {
            "event_type": "image.exists",
            "timestamp": "2013-06-20 18:31:57.939614",
            "publisher_id": "glance-api01-r2961.global.preprod-ord.ohthree.com",
            "message_id": "d14cfa51-6a0e-4cf8-9130-804738be96d2",
            "payload": {
                "audit_period_beginning": audit_period_beginning,
                "audit_period_ending": audit_period_ending,
                "owner": TENANT_ID_1,
                "images":
                [
                    {
                        "created_at": created_at,
                        "id": uuid,
                        "size": size,
                        "status": "saving",
                        "properties": {"instance_uuid": INSTANCE_ID_1},
                        "deleted_at": deleted_at,
                    },
                    {
                        "created_at": created_at,
                        "id": uuid,
                        "size": size,
                        "status": "saving",
                        "properties": {"instance_uuid": INSTANCE_ID_1},
                        "deleted_at": deleted_at,
                    }
                ]
            }
        }
        deployment = "1"
        routing_key = "glance_monitor.info"
        json_body = json.dumps([routing_key, body])
        self.mox.StubOutWithMock(db, 'create_image_exists')
        self.mox.StubOutWithMock(db, 'get_image_usage')
        self.mox.StubOutWithMock(db, 'get_image_delete')

        for i in range(0, 2):
            db.get_image_usage(uuid=uuid).AndReturn(None)
            db.get_image_delete(uuid=uuid).AndReturn(delete)
            db.create_image_exists(
                created_at=utils.str_time_to_unix(created_at),
                owner=TENANT_ID_1,
                raw=raw,
                audit_period_beginning=utils.str_time_to_unix(audit_period_beginning),
                audit_period_ending=utils.str_time_to_unix(audit_period_ending),
                size=size,
                uuid=uuid,
                usage=None,
                delete=delete,
                deleted_at=utils.str_time_to_unix(deleted_at),
                message_id="d14cfa51-6a0e-4cf8-9130-804738be96d2").AndReturn(raw)

        self.mox.ReplayAll()

        notification = GlanceNotification(body, deployment, routing_key,
                                          json_body)
        notification.save_exists(raw)
        self.mox.VerifyAll()

    def test_save_image_exists_without_created_at(self):
        raw = self.mox.CreateMockAnything()
        raw.id = 1
        audit_period_beginning = "2013-05-20 17:31:57.939614"
        audit_period_ending = "2013-06-20 17:31:57.939614"
        size = 123
        uuid = "2df2ccf6-bc1b-4853-aab0-25fda346b3bb"
        body = {
            "event_type": "image.exists",
            "timestamp": "2013-06-20 18:31:57.939614",
            "publisher_id": "glance-api01-r2961.global.preprod-ord.ohthree.com",
            "payload": {
                "audit_period_beginning": audit_period_beginning,
                "audit_period_ending": audit_period_ending,
                "owner": TENANT_ID_1,
                "images":
                [
                    {
                        "created_at": None,
                        "id": uuid,
                        "size": size,
                        "status": "saving",
                        "properties": {"instance_uuid": INSTANCE_ID_1},
                        "deleted_at": None,
                    },
                    {
                        "created_at": None,
                        "id": uuid,
                        "size": size,
                        "status": "saving",
                        "properties": {"instance_uuid": INSTANCE_ID_1},
                        "deleted_at": None,
                    }
                ]
            }
        }
        deployment = "1"
        routing_key = "glance_monitor.info"
        json_body = json.dumps([routing_key, body])
        self.mox.StubOutWithMock(stacklog, 'warn')
        stacklog.warn("Ignoring exists without created_at. GlanceRawData(1)")
        stacklog.warn("Ignoring exists without created_at. GlanceRawData(1)")
        self.mox.ReplayAll()

        notification = GlanceNotification(body, deployment, routing_key,
                                          json_body)
        notification.save_exists(raw)
        self.mox.VerifyAll()

    def test_save_exists_should_log_warning_when_payload_is_invalid(self):
        raw = self.mox.CreateMockAnything()
        raw.id = 1
        body = {
            "event_type": "image.exists",
            "publisher_id": "glance-api01-r2961.global.preprod-ord.ohthree.com",
            "payload": []
        }
        deployment = "1"
        routing_key = "glance_monitor.info"
        json_body = json.dumps([routing_key, body])
        self.mox.StubOutWithMock(stacklog, 'warn')
        stacklog.warn("Received exists with invalid payload GlanceRawData(1)")
        self.mox.ReplayAll()

        notification = GlanceNotification(body, deployment, routing_key,
                                          json_body)
        notification.save_exists(raw)
        self.mox.VerifyAll()
