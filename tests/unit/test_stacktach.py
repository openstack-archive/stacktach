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
import json

import mox

import utils
from utils import BANDWIDTH_PUBLIC_OUTBOUND
from utils import INSTANCE_FLAVOR_ID_1
from utils import INSTANCE_FLAVOR_ID_2
from utils import INSTANCE_ID_1
from utils import OS_VERSION_1
from utils import OS_ARCH_1
from utils import OS_DISTRO_1
from utils import RAX_OPTIONS_1
from utils import MESSAGE_ID_1
from utils import REQUEST_ID_1
from utils import TENANT_ID_1
from utils import INSTANCE_TYPE_ID_1
from utils import DUMMY_TIME
from utils import INSTANCE_TYPE_ID_2
from stacktach import stacklog, models
from stacktach import notification
from stacktach import views
from tests.unit import StacktachBaseTestCase


class StacktachRawParsingTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        views.STACKDB = self.mox.CreateMockAnything()

    def tearDown(self):
        self.mox.UnsetStubs()

    def assertOnHandlerResponse(self, resp, **kwargs):
        for key in kwargs:
            self.assertTrue(key in resp, msg='%s not in response' % key)
            self.assertEqual(resp[key], kwargs[key])

    def test_process_raw_data(self):
        deployment = self.mox.CreateMockAnything()
        when = '2013-1-25 13:38:23.123'
        dict = {
            'timestamp': when,
        }
        routing_key = 'monitor.info'
        args = (routing_key, dict)
        json_args = json.dumps(args)
        mock_record = self.mox.CreateMockAnything()
        mock_notification = self.mox.CreateMockAnything()
        mock_notification.save().AndReturn(mock_record)
        self.mox.StubOutWithMock(notification, 'notification_factory')
        exchange = 'nova'
        notification.notification_factory(dict, deployment, routing_key,
                                          json_args, exchange).AndReturn(
            mock_notification)
        self.mox.ReplayAll()

        self.assertEquals(
            views.process_raw_data(deployment, args, json_args, exchange),
                                  (mock_record, mock_notification))
        self.mox.VerifyAll()

    def test_process_raw_data_old_timestamp(self):
        deployment = self.mox.CreateMockAnything()
        when = '2013-1-25T13:38:23.123'
        dict = {
            '_context_timestamp': when,
        }
        routing_key = 'monitor.info'
        args = ('monitor.info', dict)
        json_args = json.dumps(args[1])

        mock_notification = self.mox.CreateMockAnything()
        mock_notification.save()
        self.mox.StubOutWithMock(notification, 'notification_factory')
        exchange = 'nova'
        notification.notification_factory(dict, deployment, routing_key,
                                          json_args, exchange).AndReturn(mock_notification)
        self.mox.ReplayAll()

        views.process_raw_data(deployment, args, json_args, exchange)
        self.mox.VerifyAll()


class StacktachLifecycleTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        views.STACKDB = self.mox.CreateMockAnything()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_start_kpi_tracking_not_update(self):
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.create.start'
        self.mox.ReplayAll()
        views.start_kpi_tracking(None, raw)
        self.mox.VerifyAll()

    def test_start_kpi_tracking_not_from_api(self):
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.update'
        raw.service = 'compute'
        self.mox.ReplayAll()
        views.start_kpi_tracking(None, raw)
        self.mox.VerifyAll()

    def test_start_kpi_tracking(self):
        lifecycle = self.mox.CreateMockAnything()
        tracker = self.mox.CreateMockAnything()
        when = utils.decimal_utc()
        raw = utils.create_raw(self.mox, when, 'compute.instance.update',
                               host='nova.example.com', service='api')
        views.STACKDB.create_request_tracker(lifecycle=lifecycle,
                                             request_id=REQUEST_ID_1,
                                             start=when,
                                             last_timing=None,
                                             duration=str(0.0))\
                                             .AndReturn(tracker)
        views.STACKDB.save(tracker)
        self.mox.ReplayAll()
        views.start_kpi_tracking(lifecycle, raw)
        self.mox.VerifyAll()

    def test_start_kpi_tracking_not_using_host(self):
        lifecycle = self.mox.CreateMockAnything()
        tracker = self.mox.CreateMockAnything()
        when = utils.decimal_utc()
        raw = utils.create_raw(self.mox, when, 'compute.instance.update',
                               host='api.example.com', service='compute')
        self.mox.ReplayAll()
        views.start_kpi_tracking(lifecycle, raw)
        self.mox.VerifyAll()

    def test_update_kpi_no_trackers(self):
        raw = self.mox.CreateMockAnything()
        raw.request_id = REQUEST_ID_1
        views.STACKDB.find_request_trackers(request_id=REQUEST_ID_1)\
                     .AndReturn([])
        self.mox.ReplayAll()
        views.update_kpi(None, raw)
        self.mox.VerifyAll()

    def test_update_kpi(self):
        lifecycle = self.mox.CreateMockAnything()
        end = utils.decimal_utc()
        raw = self.mox.CreateMockAnything()
        raw.request_id = REQUEST_ID_1
        raw.when=end
        timing = utils.create_timing(self.mox, 'compute.instance.create',
                                     lifecycle, end_when=end)
        start = utils.decimal_utc()
        tracker = utils.create_tracker(self.mox, REQUEST_ID_1, lifecycle,
                                       start)
        views.STACKDB.find_request_trackers(request_id=REQUEST_ID_1)\
                      .AndReturn([tracker])
        views.STACKDB.save(tracker)
        self.mox.ReplayAll()
        views.update_kpi(timing, raw)
        self.assertEqual(tracker.request_id, REQUEST_ID_1)
        self.assertEqual(tracker.lifecycle, lifecycle)
        self.assertEqual(tracker.last_timing, timing)
        self.assertEqual(tracker.start, start)
        self.assertEqual(tracker.duration, end-start)
        self.mox.VerifyAll()

    def test_aggregate_lifecycle_no_instance(self):
        raw = self.mox.CreateMockAnything()
        raw.instance = None
        self.mox.ReplayAll()
        views.aggregate_lifecycle(raw)
        self.mox.VerifyAll()

    def test_aggregate_lifecycle_start(self):
        event_name = 'compute.instance.create'
        event = '%s.start' % event_name
        when = datetime.datetime.utcnow()
        raw = utils.create_raw(self.mox, when, event, state='building')

        views.STACKDB.find_lifecycles(instance=INSTANCE_ID_1).AndReturn([])
        lifecycle = self.mox.CreateMockAnything()
        lifecycle.instance = INSTANCE_ID_1
        views.STACKDB.create_lifecycle(instance=INSTANCE_ID_1)\
                     .AndReturn(lifecycle)
        views.STACKDB.save(lifecycle)

        views.STACKDB.find_timings(name=event_name, lifecycle=lifecycle)\
                     .AndReturn([])
        timing = utils.create_timing(self.mox, event_name, lifecycle)
        views.STACKDB.create_timing(lifecycle=lifecycle, name=event_name)\
                     .AndReturn(timing)
        views.STACKDB.save(timing)

        self.mox.ReplayAll()
        views.aggregate_lifecycle(raw)
        self.assertEqual(lifecycle.last_raw, raw)
        self.assertEqual(lifecycle.last_state, 'building')
        self.assertEqual(lifecycle.last_task_state, '')
        self.assertEqual(timing.name, event_name)
        self.assertEqual(timing.lifecycle, lifecycle)
        self.assertEqual(timing.start_raw, raw)
        self.assertEqual(timing.start_when, when)

        self.mox.VerifyAll()

    def test_aggregate_lifecycle_end(self):
        event_name = 'compute.instance.create'
        start_event = '%s.end' % event_name
        end_event = '%s.end' % event_name
        start_when = datetime.datetime.utcnow()
        end_when = datetime.datetime.utcnow()
        start_raw = utils.create_raw(self.mox, start_when, start_event,
                                          state='building')
        end_raw = utils.create_raw(self.mox, end_when, end_event,
                                        old_task='build')

        lifecycle = utils.create_lifecycle(self.mox, INSTANCE_ID_1,
                                                'active', '', start_raw)
        views.STACKDB.find_lifecycles(instance=INSTANCE_ID_1)\
                     .AndReturn([lifecycle])
        views.STACKDB.save(lifecycle)

        timing = utils.create_timing(self.mox, event_name, lifecycle,
                                     start_raw=start_raw,
                                     start_when=start_when)
        views.STACKDB.find_timings(name=event_name, lifecycle=lifecycle)\
                     .AndReturn([timing])

        self.mox.StubOutWithMock(views, "update_kpi")
        views.update_kpi(timing, end_raw)
        views.STACKDB.save(timing)

        self.mox.ReplayAll()
        views.aggregate_lifecycle(end_raw)
        self.assertEqual(lifecycle.last_raw, end_raw)
        self.assertEqual(lifecycle.last_state, 'active')
        self.assertEqual(lifecycle.last_task_state, 'build')
        self.assertEqual(timing.name, event_name)
        self.assertEqual(timing.lifecycle, lifecycle)
        self.assertEqual(timing.start_raw, start_raw)
        self.assertEqual(timing.start_when, start_when)
        self.assertEqual(timing.end_raw, end_raw)
        self.assertEqual(timing.end_when, end_when)
        self.assertEqual(timing.diff, end_when-start_when)

        self.mox.VerifyAll()

    def test_aggregate_lifecycle_update(self):
        event = 'compute.instance.update'
        when = datetime.datetime.utcnow()
        raw = utils.create_raw(self.mox, when, event, old_task='reboot')

        views.STACKDB.find_lifecycles(instance=INSTANCE_ID_1).AndReturn([])
        lifecycle = self.mox.CreateMockAnything()
        lifecycle.instance = INSTANCE_ID_1
        views.STACKDB.create_lifecycle(instance=INSTANCE_ID_1).AndReturn(lifecycle)
        views.STACKDB.save(lifecycle)

        self.mox.StubOutWithMock(views, "start_kpi_tracking")
        views.start_kpi_tracking(lifecycle, raw)

        self.mox.ReplayAll()
        views.aggregate_lifecycle(raw)
        self.assertEqual(lifecycle.last_raw, raw)
        self.assertEqual(lifecycle.last_state, 'active')
        self.assertEqual(lifecycle.last_task_state, 'reboot')

        self.mox.VerifyAll()


class StacktachUsageParsingTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        views.STACKDB = self.mox.CreateMockAnything()
        self.log = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(stacklog, 'get_logger')

    def tearDown(self):
        self.mox.UnsetStubs()

    def setup_mock_log(self, name=None):
        if name is None:
            stacklog.get_logger(name=mox.IgnoreArg(),
                                is_parent=False).AndReturn(self.log)
        else:
            stacklog.get_logger(name=name,
                                is_parent=False).AndReturn(self.log)

    def test_all_instance_events_have_mapping(self):
        for key, value in views.INSTANCE_EVENT.items():
            msg = "'%s' does not have a process function mapping." % value
            self.assertTrue(value in views.USAGE_PROCESS_MAPPING, msg)

    def _create_mock_notification(self):
        notification = self.mox.CreateMockAnything()
        notification.launched_at = str(DUMMY_TIME)
        notification.tenant = TENANT_ID_1
        notification.rax_options = RAX_OPTIONS_1
        notification.os_architecture = OS_ARCH_1
        notification.os_version = OS_VERSION_1
        notification.os_distro = OS_DISTRO_1
        notification.instance = INSTANCE_ID_1
        notification.request_id = REQUEST_ID_1
        notification.instance_type_id = INSTANCE_TYPE_ID_1
        notification.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        return notification

    def test_process_usage_for_new_launch_create_start(self):
        notification = self._create_mock_notification()
        notification.instance_flavor_id = INSTANCE_FLAVOR_ID_1

        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.create.start'

        usage = self.mox.CreateMockAnything()
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_new_launch(raw, notification)

        self.assertEquals(usage.instance_type_id, INSTANCE_TYPE_ID_1)
        self.assertEquals(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)
        self.assertEquals(usage.instance_flavor_id, INSTANCE_FLAVOR_ID_1)

        self.mox.VerifyAll()

    def test_process_usage_for_new_launch_rescue_start(self):
        notification = self._create_mock_notification()

        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.rescue.start'

        usage = self.mox.CreateMockAnything()
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_new_launch(raw, notification)

        self.assertEquals(usage.instance_type_id, INSTANCE_TYPE_ID_1)
        self.assertEquals(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_usage_for_new_launch_rebuild_start(self):
        notification = self._create_mock_notification()
        notification.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.rebuild.start'
        usage = self.mox.CreateMockAnything()
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_new_launch(raw, notification)

        self.assertEquals(usage.instance_type_id, INSTANCE_TYPE_ID_1)
        self.assertEquals(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)
        self.assertEquals(usage.instance_flavor_id, INSTANCE_FLAVOR_ID_1)
        self.mox.VerifyAll()

    def test_process_usage_for_new_launch_rebuild_start_when_no_launched_at_in_db(self):
        notification = self._create_mock_notification()
        notification.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.rebuild.start'

        usage = self.mox.CreateMockAnything()
        usage.launched_at = None
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_new_launch(raw, notification)

        self.assertEqual(usage.launched_at, utils.decimal_utc(DUMMY_TIME))
        self.assertEquals(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)
        self.assertEquals(usage.instance_flavor_id, INSTANCE_FLAVOR_ID_1)

        self.mox.VerifyAll()

    def test_process_usage_for_new_launch_resize_prep_start_when_no_launched_at_in_db(self):
        notification = self._create_mock_notification()
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.resize.prep.start'

        usage = self.mox.CreateMockAnything()
        usage.launched_at = None
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        usage.launched_at = None

        views._process_usage_for_new_launch(raw, notification)

        self.assertEqual(usage.launched_at, utils.decimal_utc(DUMMY_TIME))
        self.assertEquals(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_usage_for_new_launch_resize_revert_start_when_no_launched_at_in_db(self):
        notification = self._create_mock_notification()
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.resize.revert.start'

        usage = self.mox.CreateMockAnything()
        usage.launched_at = None
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_new_launch(raw, notification)

        self.assertEquals(usage.tenant, TENANT_ID_1)
        self.assertEqual(usage.launched_at, utils.decimal_utc(DUMMY_TIME))
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_usage_for_new_launch_resize_prep_start_when_launched_at_in_db(self):
        notification = self._create_mock_notification()
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.resize.prep.start'

        orig_launched_at = utils.decimal_utc(DUMMY_TIME - datetime.timedelta(days=1))
        usage = self.mox.CreateMockAnything()
        usage.launched_at = orig_launched_at
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_new_launch(raw, notification)

        self.assertEqual(usage.launched_at, orig_launched_at)
        self.assertEqual(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_usage_for_new_launch_rescue_start_when_launched_at_in_db(self):
        notification = self._create_mock_notification()
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.rescue.start'

        orig_launched_at = utils.decimal_utc(DUMMY_TIME - datetime.timedelta(days=1))
        usage = self.mox.CreateMockAnything()
        usage.launched_at = orig_launched_at
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_new_launch(raw, notification)

        self.assertEqual(usage.launched_at, orig_launched_at)
        self.assertEqual(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_usage_for_updates_create_end(self):
        notification = self._create_mock_notification()
        notification.message = 'Success'
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.create.end'

        usage = self.mox.CreateMockAnything()
        usage.launched_at = None
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw, notification)

        self.assertEqual(usage.launched_at, utils.decimal_utc(DUMMY_TIME))
        self.assertEqual(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_usage_for_updates_rescue_end(self):
        notification = self._create_mock_notification()
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.rescue.end'

        usage = self.mox.CreateMockAnything()
        usage.launched_at = None
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw, notification)

        self.assertEqual(usage.launched_at, utils.decimal_utc(DUMMY_TIME))
        self.assertEqual(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_usage_for_updates_create_end_success_message(self):
        notification = self._create_mock_notification()
        notification.message = 'Success'
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.create.end'

        usage = self.mox.CreateMockAnything()
        usage.launched_at = None
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw, notification)
        self.assertEqual(usage.launched_at, utils.decimal_utc(DUMMY_TIME))
        self.assertEqual(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_usage_for_updates_create_end_error_message(self):
        notification = self.mox.CreateMockAnything()
        notification.message = 'Error'

        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.create.end'
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw, notification)

        self.mox.VerifyAll()

    def test_process_usage_for_updates_revert_end(self):
        notification = self._create_mock_notification()
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.resize.revert.end'

        usage = self.mox.CreateMockAnything()
        usage.launched_at = None
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw, notification)

        self.assertEqual(usage.instance_type_id, INSTANCE_TYPE_ID_1)
        self.assertEqual(usage.launched_at, utils.decimal_utc(DUMMY_TIME))
        self.assertEquals(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_usage_for_updates_finish_resize_start(self):
        notification = self._create_mock_notification()
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.finish_resize.start'

        usage = self.mox.CreateMockAnything()
        usage.launched_at = None
        usage.instance_type_id = INSTANCE_TYPE_ID_2
        usage.instance_flavor_id = INSTANCE_FLAVOR_ID_2
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw, notification)

        self.assertEqual(usage.instance_type_id, INSTANCE_TYPE_ID_1)
        self.assertEqual(usage.instance_flavor_id, INSTANCE_FLAVOR_ID_1)
        self.assertEquals(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_usage_for_updates_finish_resize_end(self):
        notification = self._create_mock_notification()
        raw = self.mox.CreateMockAnything()
        raw.event = 'compute.instance.finish_resize.end'

        usage = self.mox.CreateMockAnything()
        usage.launched_at = None
        usage.instance_type_id = INSTANCE_TYPE_ID_2
        usage.instance_flavor_id = INSTANCE_FLAVOR_ID_2
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1) \
            .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw, notification)

        self.assertEqual(usage.instance_type_id, INSTANCE_TYPE_ID_1)
        self.assertEqual(usage.instance_flavor_id, INSTANCE_FLAVOR_ID_1)
        self.assertEquals(usage.tenant, TENANT_ID_1)
        self.assertEquals(usage.os_architecture, OS_ARCH_1)
        self.assertEquals(usage.os_version, OS_VERSION_1)
        self.assertEquals(usage.os_distro, OS_DISTRO_1)
        self.assertEquals(usage.rax_options, RAX_OPTIONS_1)

        self.mox.VerifyAll()

    def test_process_delete(self):
        delete_time = datetime.datetime.utcnow()
        terminated_time = delete_time-datetime.timedelta(seconds=1)
        launch_time = delete_time-datetime.timedelta(days=1)
        launch_decimal = utils.decimal_utc(launch_time)
        delete_decimal = utils.decimal_utc(delete_time)
        notification = self.mox.CreateMockAnything()
        notification.instance = INSTANCE_ID_1
        notification.deleted_at = str(delete_time)
        notification.terminated_at = str(terminated_time)
        notification.launched_at = str(launch_time)

        raw = self.mox.CreateMockAnything()
        delete = self.mox.CreateMockAnything()
        delete.instance = INSTANCE_ID_1
        delete.launched_at = launch_decimal
        delete.deleted_at = delete_decimal
        views.STACKDB.get_or_create_instance_delete(
            instance=INSTANCE_ID_1, deleted_at=delete_decimal,
            launched_at=launch_decimal)\
            .AndReturn((delete, True))
        views.STACKDB.save(delete)
        self.mox.ReplayAll()

        views._process_delete(raw, notification)

        self.assertEqual(delete.instance, INSTANCE_ID_1)
        self.assertEqual(delete.launched_at, launch_decimal)
        self.assertEqual(delete.deleted_at, delete_decimal)
        self.mox.VerifyAll()

    def test_process_delete_with_only_terminated_at(self):
        delete_time = datetime.datetime.utcnow()
        launch_time = delete_time-datetime.timedelta(days=1)
        launch_decimal = utils.decimal_utc(launch_time)
        delete_decimal = utils.decimal_utc(delete_time)
        notification = self.mox.CreateMockAnything()
        notification.instance = INSTANCE_ID_1
        notification.deleted_at = ''
        notification.terminated_at = str(delete_time)
        notification.launched_at = str(launch_time)

        raw = self.mox.CreateMockAnything()
        delete = self.mox.CreateMockAnything()
        delete.instance = INSTANCE_ID_1
        delete.launched_at = launch_decimal
        delete.deleted_at = delete_decimal
        views.STACKDB.get_or_create_instance_delete(
            instance=INSTANCE_ID_1, deleted_at=delete_decimal,
            launched_at=launch_decimal)\
            .AndReturn((delete, True))
        views.STACKDB.save(delete)
        self.mox.ReplayAll()

        views._process_delete(raw, notification)

        self.assertEqual(delete.instance, INSTANCE_ID_1)
        self.assertEqual(delete.launched_at, launch_decimal)
        self.assertEqual(delete.deleted_at, delete_decimal)
        self.mox.VerifyAll()

    def test_process_delete_with_neither(self):
        delete_time = datetime.datetime.utcnow()
        launch_time = delete_time-datetime.timedelta(days=1)
        launch_decimal = utils.decimal_utc(launch_time)
        delete_decimal = utils.decimal_utc(delete_time)
        notification = self.mox.CreateMockAnything()
        notification.instance = INSTANCE_ID_1
        notification.deleted_at = ''
        notification.terminated_at = str(delete_time)
        notification.launched_at = str(launch_time)

        raw = self.mox.CreateMockAnything()
        delete = self.mox.CreateMockAnything()
        delete.instance = INSTANCE_ID_1
        delete.launched_at = launch_decimal
        delete.deleted_at = delete_decimal
        views.STACKDB.get_or_create_instance_delete(
            instance=INSTANCE_ID_1, deleted_at=delete_decimal,
            launched_at=launch_decimal)\
            .AndReturn((delete, True))
        views.STACKDB.save(delete)
        self.mox.ReplayAll()

        views._process_delete(raw, notification)

        self.assertEqual(delete.instance, INSTANCE_ID_1)
        self.assertEqual(delete.launched_at, launch_decimal)
        self.assertEqual(delete.deleted_at, delete_decimal)
        self.mox.VerifyAll()

    def test_process_delete_no_launch(self):
        delete_time = datetime.datetime.utcnow()
        notification = self.mox.CreateMockAnything()
        notification.instance = INSTANCE_ID_1
        notification.deleted_at = str(delete_time)
        notification.launched_at = ''

        raw = self.mox.CreateMockAnything()
        self.mox.ReplayAll()

        views._process_delete(raw, notification)

        self.mox.VerifyAll()

    def _create_exists_notification(self, audit_beginning, current_time,
                                    launch_time, deleted_time):
        notification = self.mox.CreateMockAnything()
        notification.launched_at = str(launch_time)
        notification.deleted_at = str(deleted_time)
        notification.audit_period_beginning = str(audit_beginning)
        notification.audit_period_ending = str(current_time)
        notification.tenant = TENANT_ID_1
        notification.os_architecture = OS_ARCH_1
        notification.os_version = OS_VERSION_1
        notification.os_distro = OS_DISTRO_1
        notification.rax_options = RAX_OPTIONS_1
        notification.instance = INSTANCE_ID_1
        notification.instance_type_id = INSTANCE_TYPE_ID_1
        notification.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        notification.message_id = MESSAGE_ID_1
        notification.bandwidth_public_out = BANDWIDTH_PUBLIC_OUTBOUND
        return notification

    def test_process_exists(self):
        current_time = datetime.datetime.utcnow()
        launch_time = current_time - datetime.timedelta(hours=23)
        launch_decimal = utils.decimal_utc(launch_time)
        audit_beginning = current_time - datetime.timedelta(hours=20)
        audit_beginning_decimal = utils.decimal_utc(audit_beginning)
        audit_ending_decimal = utils.decimal_utc(current_time)
        notification = self._create_exists_notification(
            audit_beginning, current_time, launch_time, deleted_time='')
        raw = self.mox.CreateMockAnything()
        usage = self.mox.CreateMockAnything()
        launched_range = (launch_decimal, launch_decimal+1)
        views.STACKDB.get_instance_usage(
            instance=INSTANCE_ID_1,
            launched_at__range=launched_range).AndReturn(usage)
        exists_values = {
            'message_id': MESSAGE_ID_1,
            'instance': INSTANCE_ID_1,
            'launched_at': launch_decimal,
            'audit_period_beginning': audit_beginning_decimal,
            'audit_period_ending': audit_ending_decimal,
            'instance_type_id': INSTANCE_TYPE_ID_1,
            'instance_flavor_id': INSTANCE_FLAVOR_ID_1,
            'usage': usage,
            'raw': raw,
            'tenant': TENANT_ID_1,
            'rax_options': RAX_OPTIONS_1,
            'os_architecture': OS_ARCH_1,
            'os_version': OS_VERSION_1,
            'os_distro': OS_DISTRO_1,
            'bandwidth_public_out': BANDWIDTH_PUBLIC_OUTBOUND
        }
        exists = self.mox.CreateMockAnything()
        views.STACKDB.create_instance_exists(**exists_values).AndReturn(exists)
        views.STACKDB.save(exists)
        self.mox.ReplayAll()
        views._process_exists(raw, notification)
        self.mox.VerifyAll()

    def test_process_exists_no_launched_at(self):
        notification = self.mox.CreateMockAnything()
        notification.instance = INSTANCE_ID_1
        notification.launched_at = None
        raw = self.mox.CreateMockAnything()
        raw.id = '1'
        self.setup_mock_log()
        self.log.warn('Ignoring exists without launched_at. RawData(1)')
        self.mox.ReplayAll()
        views._process_exists(raw, notification)
        self.mox.VerifyAll()

    def test_process_exists_with_deleted_at(self):
        current_time = datetime.datetime.utcnow()
        launch_time = current_time - datetime.timedelta(hours=23)
        launch_decimal = utils.decimal_utc(launch_time)
        delete_time = datetime.datetime.utcnow()
        deleted_decimal = utils.decimal_utc(delete_time)
        audit_beginning = current_time - datetime.timedelta(hours=20)
        audit_beginning_decimal = utils.decimal_utc(audit_beginning)
        audit_ending_decimal = utils.decimal_utc(current_time)
        notification = self._create_exists_notification(
            audit_beginning, current_time, launch_time, delete_time)
        raw = self.mox.CreateMockAnything()
        usage = self.mox.CreateMockAnything()
        launched_range = (launch_decimal, launch_decimal+1)
        views.STACKDB.get_instance_usage(instance=INSTANCE_ID_1,
                                         launched_at__range=launched_range)\
                     .AndReturn(usage)
        delete = self.mox.CreateMockAnything()
        views.STACKDB.get_instance_delete(instance=INSTANCE_ID_1,
                                          launched_at__range=launched_range)\
             .AndReturn(delete)
        exists_values = {
            'message_id': MESSAGE_ID_1,
            'instance': INSTANCE_ID_1,
            'launched_at': launch_decimal,
            'deleted_at': deleted_decimal,
            'audit_period_beginning': audit_beginning_decimal,
            'audit_period_ending': audit_ending_decimal,
            'instance_type_id': INSTANCE_TYPE_ID_1,
            'instance_flavor_id': INSTANCE_FLAVOR_ID_1,
            'usage': usage,
            'delete': delete,
            'raw': raw,
            'tenant': TENANT_ID_1,
            'rax_options': RAX_OPTIONS_1,
            'os_architecture': OS_ARCH_1,
            'os_version': OS_VERSION_1,
            'os_distro': OS_DISTRO_1,
            'bandwidth_public_out': BANDWIDTH_PUBLIC_OUTBOUND
        }
        exists = self.mox.CreateMockAnything()
        views.STACKDB.create_instance_exists(**exists_values).AndReturn(exists)
        views.STACKDB.save(exists)
        self.mox.ReplayAll()
        views._process_exists(raw, notification)
        self.mox.VerifyAll()


class StacktachImageUsageParsingTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        views.STACKDB = self.mox.CreateMockAnything()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_save_image_usage(self):
        raw = self.mox.CreateMockAnything()
        notification = self.mox.CreateMockAnything()
        notification.save_usage(raw)
        self.mox.ReplayAll()

        views._process_glance_usage(raw, notification)
        self.mox.VerifyAll()

    def test_save_image_delete(self):
        raw = self.mox.CreateMockAnything()
        notification = self.mox.CreateMockAnything()
        notification.save_delete(raw)
        self.mox.ReplayAll()

        views._process_glance_delete(raw, notification)
        self.mox.VerifyAll()

    def test_save_image_exists(self):
        raw = self.mox.CreateMockAnything()
        notification = self.mox.CreateMockAnything()
        notification.save_exists(raw)
        self.mox.ReplayAll()

        views._process_glance_exists(raw, notification)
        self.mox.VerifyAll()
