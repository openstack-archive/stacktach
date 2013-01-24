import datetime
import json
import os
import sys
import unittest

import mox

import utils
utils.setup_sys_path()
from utils import INSTANCE_ID_1
from utils import INSTANCE_ID_2
from utils import MESSAGE_ID_1
from utils import MESSAGE_ID_2
from utils import REQUEST_ID_1
from utils import REQUEST_ID_2
from utils import REQUEST_ID_3
from stacktach import views

class StacktachLifecycleTestCase(unittest.TestCase):
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
        raw.host = 'compute'
        self.mox.ReplayAll()
        views.start_kpi_tracking(None, raw)
        self.mox.VerifyAll()

    def test_start_kpi_tracking(self):
        lifecycle = self.mox.CreateMockAnything()
        tracker = self.mox.CreateMockAnything()
        when = utils.decimal_utc()
        raw = utils.create_raw(self.mox, when, 'compute.instance.update',
                               host='api')
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


class StacktackUsageParsingTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()
        views.STACKDB = self.mox.CreateMockAnything()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_process_usage_for_new_launch(self):
        when = utils.decimal_utc()
        notif = utils.create_nova_notif(request_id=REQUEST_ID_1)
        json_str = json.dumps(notif)
        event = 'compute.instance.create.start'
        raw = utils.create_raw(self.mox, when, event=event, json_str=json_str)
        usage = self.mox.CreateMockAnything()
        views.STACKDB.create_instance_usage(instance=INSTANCE_ID_1,
                                            request_id=REQUEST_ID_1,
                                            instance_type_id = '1')\
                     .AndReturn(usage)
        views.STACKDB.save(usage)
        self.mox.ReplayAll()
        views._process_usage_for_new_launch(raw)
        self.mox.VerifyAll()

    def test_process_usage_for_updates_create_end(self):
        when_time = datetime.datetime.utcnow()
        when_str = str(when_time)
        when_decimal = utils.decimal_utc(when_time)
        notif = utils.create_nova_notif(request_id=REQUEST_ID_1,
                                        launched=str(when_time))
        json_str = json.dumps(notif)
        event = 'compute.instance.create.end'
        raw = utils.create_raw(self.mox, when_decimal, event=event,
                               json_str=json_str)
        usage = self.mox.CreateMockAnything()
        usage.instance = INSTANCE_ID_1
        usage.request_id = REQUEST_ID_1
        usage.instance_type_id = '1'
        views.STACKDB.get_instance_usage(instance=INSTANCE_ID_1,
                                         request_id=REQUEST_ID_1)\
                     .AndReturn(usage)
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw)
        self.assertEqual(usage.instance, INSTANCE_ID_1)
        self.assertEqual(usage.request_id, REQUEST_ID_1)
        self.assertEqual(usage.instance_type_id, '1')
        self.assertEqual(usage.launched_at, when_decimal)
        self.mox.VerifyAll()

    def test_process_usage_for_updates_revert_end(self):
        when_time = datetime.datetime.utcnow()
        when_decimal = utils.decimal_utc(when_time)
        notif = utils.create_nova_notif(request_id=REQUEST_ID_1,
                                        launched=str(when_time))
        json_str = json.dumps(notif)
        event = 'compute.instance.resize.revert.end'
        raw = utils.create_raw(self.mox, when_decimal, event=event,
                               json_str=json_str)
        usage = self.mox.CreateMockAnything()
        usage.instance = INSTANCE_ID_1
        usage.request_id = REQUEST_ID_1
        usage.instance_type_id = '1'
        views.STACKDB.get_instance_usage(instance=INSTANCE_ID_1,
                                         request_id=REQUEST_ID_1)\
                     .AndReturn(usage)
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw)
        self.assertEqual(usage.instance, INSTANCE_ID_1)
        self.assertEqual(usage.request_id, REQUEST_ID_1)
        self.assertEqual(usage.instance_type_id, '1')
        self.assertEqual(usage.launched_at, when_decimal)
        self.mox.VerifyAll()

    def test_process_usage_for_updates_prep_end(self):
        when_time = datetime.datetime.utcnow()
        when_decimal = utils.decimal_utc(when_time)
        notif = utils.create_nova_notif(request_id=REQUEST_ID_1,
                                        new_type_id='2')
        json_str = json.dumps(notif)
        event = 'compute.instance.resize.prep.end'
        raw = utils.create_raw(self.mox, when_decimal, event=event,
                               json_str=json_str)
        usage = self.mox.CreateMockAnything()
        usage.instance = INSTANCE_ID_1
        usage.request_id = REQUEST_ID_1
        views.STACKDB.get_instance_usage(instance=INSTANCE_ID_1,
                                         request_id=REQUEST_ID_1)\
                     .AndReturn(usage)
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw)
        self.assertEqual(usage.instance, INSTANCE_ID_1)
        self.assertEqual(usage.request_id, REQUEST_ID_1)
        self.assertEqual(usage.instance_type_id, '2')
        self.mox.VerifyAll()

    def test_process_delete(self):
        delete_time = datetime.datetime.utcnow()
        launch_time = delete_time-datetime.timedelta(days=1)
        launch_decimal = utils.decimal_utc(launch_time)
        delete_decimal = utils.decimal_utc(delete_time)
        notif = utils.create_nova_notif(request_id=REQUEST_ID_1,
                                        launched=str(launch_time),
                                        deleted=str(delete_time))
        json_str = json.dumps(notif)
        event = 'compute.instance.delete.end'
        raw = utils.create_raw(self.mox, delete_decimal, event=event,
                               json_str=json_str)
        usage = self.mox.CreateMockAnything()
        usage.instance = INSTANCE_ID_1
        usage.request_id = REQUEST_ID_1
        usage.instance_type_id = '1'
        usage.launched_at = launch_decimal
        views.STACKDB.get_instance_usage(instance=INSTANCE_ID_1,
                                         launched_at=launch_decimal)\
                     .AndReturn(usage)
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_delete(raw)
        self.assertEqual(usage.instance, INSTANCE_ID_1)
        self.assertEqual(usage.request_id, REQUEST_ID_1)
        self.assertEqual(usage.instance_type_id, '1')
        self.assertEqual(usage.launched_at, launch_decimal)
        self.assertEqual(usage.deleted_at, delete_decimal)
        self.mox.VerifyAll()

    def test_process_exists(self):
        launch_time = datetime.datetime.utcnow()-datetime.timedelta(hours=23)
        launch_decimal = utils.decimal_utc(launch_time)
        current_time = datetime.datetime.utcnow()
        current_decimal = utils.decimal_utc(current_time)
        notif = utils.create_nova_notif(launched=str(launch_time))
        json_str = json.dumps(notif)
        event = 'compute.instance.exists'
        raw = utils.create_raw(self.mox, current_decimal, event=event,
                               json_str=json_str)
        usage = self.mox.CreateMockAnything()
        views.STACKDB.get_instance_usage(instance=INSTANCE_ID_1,
                                         launched_at=launch_decimal)\
                     .AndReturn(usage)
        exists_values = {
            'message_id': MESSAGE_ID_1,
            'instance': INSTANCE_ID_1,
            'launched_at': launch_decimal,
            'instance_type_id': '1',
            'usage': usage,
            'raw': raw,
        }
        exists = self.mox.CreateMockAnything()
        views.STACKDB.create_instance_exists(**exists_values).AndReturn(exists)
        views.STACKDB.save(exists)
        self.mox.ReplayAll()
        views._process_exists(raw)
        self.mox.VerifyAll()

    def test_process_exists_with_deleted_at(self):
        launch_time = datetime.datetime.utcnow()-datetime.timedelta(hours=23)
        launch_decimal = utils.decimal_utc(launch_time)
        deleted_time = datetime.datetime.utcnow()-datetime.timedelta(hours=12)
        deleted_decimal = utils.decimal_utc(deleted_time)
        current_time = datetime.datetime.utcnow()
        current_decimal = utils.decimal_utc(current_time)
        notif = utils.create_nova_notif(launched=str(launch_time),
                                        deleted=str(deleted_time))
        json_str = json.dumps(notif)
        event = 'compute.instance.exists'
        raw = utils.create_raw(self.mox, current_decimal, event=event,
                               json_str=json_str)
        usage = self.mox.CreateMockAnything()
        views.STACKDB.get_instance_usage(instance=INSTANCE_ID_1,
                                         launched_at=launch_decimal)\
                     .AndReturn(usage)
        exists_values = {
            'message_id': MESSAGE_ID_1,
            'instance': INSTANCE_ID_1,
            'launched_at': launch_decimal,
            'deleted_at': deleted_decimal,
            'instance_type_id': '1',
            'usage': usage,
            'raw': raw,
        }
        exists = self.mox.CreateMockAnything()
        views.STACKDB.create_instance_exists(**exists_values).AndReturn(exists)
        views.STACKDB.save(exists)
        self.mox.ReplayAll()
        views._process_exists(raw)
        self.mox.VerifyAll()

