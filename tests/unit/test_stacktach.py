# Copyright 2012 - Rackspace Inc.

import datetime
import json
import os
import sys
import unittest

import mox

import utils
from utils import INSTANCE_ID_1
from utils import INSTANCE_ID_2
from utils import MESSAGE_ID_1
from utils import MESSAGE_ID_2
from utils import REQUEST_ID_1
from utils import REQUEST_ID_2
from utils import REQUEST_ID_3
from utils import TENANT_ID_1
from stacktach import views


class StacktachRawParsingTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()
        views.STACKDB = self.mox.CreateMockAnything()

    def tearDown(self):
        self.mox.UnsetStubs()

    def assertOnHandlerResponse(self, resp, **kwargs):
        for key in kwargs:
            self.assertTrue(key in resp, msg='%s not in response' % key)
            self.assertEqual(resp[key], kwargs[key])

    def test_monitor_message(self):
        body = {
            'event_type': 'compute.instance.create.start',
            'publisher_id': 'compute.cpu1-n01.example.com',
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            'payload': {
                'instance_id': INSTANCE_ID_1,
                'state': 'active',
                'old_state': 'building',
                'old_task_state': 'build',
            },
        }
        resp = views._monitor_message(None, body)
        self.assertOnHandlerResponse(resp, host='cpu1-n01.example.com',
                                     instance=INSTANCE_ID_1,
                                     publisher=body['publisher_id'],
                                     service='compute',
                                     event=body['event_type'],
                                     tenant=TENANT_ID_1,
                                     request_id=REQUEST_ID_1,
                                     state='active',
                                     old_state='building',
                                     old_task='build')

    def test_monitor_message_no_host(self):
        body = {
            'event_type': 'compute.instance.create.start',
            'publisher_id': 'compute',
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            'payload': {
                'instance_id': INSTANCE_ID_1,
                'state': 'active',
                'old_state': 'building',
                'old_task_state': 'build',
                },
            }
        resp = views._monitor_message(None, body)
        self.assertOnHandlerResponse(resp, host=None, instance=INSTANCE_ID_1,
                                     publisher=body['publisher_id'],
                                     service='compute',
                                     event=body['event_type'],
                                     tenant=TENANT_ID_1,
                                     request_id=REQUEST_ID_1, state='active',
                                     old_state='building', old_task='build')

    def test_monitor_message_exception(self):
        body = {
            'event_type': 'compute.instance.create.start',
            'publisher_id': 'compute.cpu1-n01.example.com',
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            'payload': {
                'exception': {'kwargs':{'uuid': INSTANCE_ID_1}},
                'state': 'active',
                'old_state': 'building',
                'old_task_state': 'build',
                },
            }
        resp = views._monitor_message(None, body)
        self.assertOnHandlerResponse(resp, host='cpu1-n01.example.com',
                                     instance=INSTANCE_ID_1,
                                     publisher=body['publisher_id'],
                                     service='compute',
                                     event=body['event_type'],
                                     tenant=TENANT_ID_1,
                                     request_id=REQUEST_ID_1,
                                     state='active', old_state='building',
                                     old_task='build')

    def test_monitor_message_exception(self):
        body = {
            'event_type': 'compute.instance.create.start',
            'publisher_id': 'compute.cpu1-n01.example.com',
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            'payload': {
                'instance': {'uuid': INSTANCE_ID_1},
                'state': 'active',
                'old_state': 'building',
                'old_task_state': 'build',
                },
            }
        resp = views._monitor_message(None, body)
        self.assertOnHandlerResponse(resp, host='cpu1-n01.example.com',
                                    instance=INSTANCE_ID_1,
                                    publisher=body['publisher_id'],
                                    service='compute',
                                    event=body['event_type'],
                                    tenant=TENANT_ID_1,
                                    request_id=REQUEST_ID_1,
                                    state='active', old_state='building',
                                    old_task='build')

    def test_compute_update_message(self):
        body = {
            '_context_request_id': REQUEST_ID_1,
            'method': 'some_method',
            'args': {
                'host': 'compute',
                'service_name': 'compute',
                '_context_project_id': TENANT_ID_1
            },
            'payload': {
                'state': 'active',
                'old_state': 'building',
                'old_task_state': 'build',
                }
        }
        resp = views._compute_update_message(None, body)
        print resp
        self.assertOnHandlerResponse(resp, publisher=None, instance=None,
                                     host='compute', tenant=TENANT_ID_1,
                                     event='some_method',
                                     request_id=REQUEST_ID_1, state='active',
                                     old_state='building', old_task='build')

    def test_process_raw_data(self):
        deployment = self.mox.CreateMockAnything()
        when = '2013-1-25 13:38:23.123'
        dict = {
            'timestamp': when,
        }
        args = ('monitor.info', dict)
        json_args = json.dumps(args)
        old_info_handler = views.HANDLERS['monitor.info']
        views.HANDLERS['monitor.info'] = lambda key, mess: {'host': 'api'}
        raw_values = {
            'deployment': deployment,
            'when': utils.decimal_utc(datetime.datetime.strptime(when, "%Y-%m-%d %H:%M:%S.%f")),
            'host': 'api',
            'routing_key': 'monitor.info',
            'json': json_args
        }
        raw = self.mox.CreateMockAnything()
        views.STACKDB.create_rawdata(**raw_values).AndReturn(raw)
        views.STACKDB.save(raw)
        self.mox.StubOutWithMock(views, "aggregate_lifecycle")
        views.aggregate_lifecycle(raw)
        self.mox.StubOutWithMock(views, "aggregate_usage")
        views.aggregate_usage(raw, dict)
        self.mox.ReplayAll()
        views.process_raw_data(deployment, args, json_args)
        self.mox.VerifyAll()
        views.HANDLERS['monitor.info'] = old_info_handler

    def test_process_raw_data_old_timestamp(self):
        deployment = self.mox.CreateMockAnything()
        when = '2013-1-25T13:38:23.123'
        dict = {
            '_context_timestamp': when,
            }
        args = ('monitor.info', dict)
        json_args = json.dumps(args)
        old_info_handler = views.HANDLERS['monitor.info']
        views.HANDLERS['monitor.info'] = lambda key, mess: {'host': 'api'}
        raw_values = {
            'deployment': deployment,
            'when': utils.decimal_utc(datetime.datetime.strptime(when, "%Y-%m-%dT%H:%M:%S.%f")),
            'host': 'api',
            'routing_key': 'monitor.info',
            'json': json_args
        }
        raw = self.mox.CreateMockAnything()
        views.STACKDB.create_rawdata(**raw_values).AndReturn(raw)
        views.STACKDB.save(raw)
        self.mox.StubOutWithMock(views, "aggregate_lifecycle")
        views.aggregate_lifecycle(raw)
        self.mox.StubOutWithMock(views, "aggregate_usage")
        views.aggregate_usage(raw, dict)
        self.mox.ReplayAll()
        views.process_raw_data(deployment, args, json_args)
        self.mox.VerifyAll()
        views.HANDLERS['monitor.info'] = old_info_handler


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
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1)\
                     .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()
        views._process_usage_for_new_launch(raw, notif[1])
        self.assertEquals(usage.instance_type_id, '1')
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
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1)\
                     .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw, notif[1])
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
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1)\
                     .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw, notif[1])
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
        views.STACKDB.get_or_create_instance_usage(instance=INSTANCE_ID_1,
                                                   request_id=REQUEST_ID_1)\
                     .AndReturn((usage, True))
        views.STACKDB.save(usage)
        self.mox.ReplayAll()

        views._process_usage_for_updates(raw, notif[1])
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
        delete = self.mox.CreateMockAnything()
        delete.instance = INSTANCE_ID_1
        delete.launched_at = launch_decimal
        delete.deleted_at = delete_decimal
        views.STACKDB.create_instance_delete(instance=INSTANCE_ID_1,
                                             launched_at=launch_decimal,
                                             deleted_at=delete_decimal,
                                             raw=raw)\
                     .AndReturn(delete)
        views.STACKDB.save(delete)
        self.mox.ReplayAll()

        views._process_delete(raw, notif[1])
        self.assertEqual(delete.instance, INSTANCE_ID_1)
        self.assertEqual(delete.launched_at, launch_decimal)
        self.assertEqual(delete.deleted_at, delete_decimal)
        self.mox.VerifyAll()

    def test_process_delete_no_launch(self):
        delete_time = datetime.datetime.utcnow()
        delete_decimal = utils.decimal_utc(delete_time)
        notif = utils.create_nova_notif(request_id=REQUEST_ID_1,
                                        deleted=str(delete_time))
        json_str = json.dumps(notif)
        event = 'compute.instance.delete.end'
        raw = utils.create_raw(self.mox, delete_decimal, event=event,
                               json_str=json_str)
        delete = self.mox.CreateMockAnything()
        delete.instance = INSTANCE_ID_1
        delete.deleted_at = delete_decimal
        views.STACKDB.create_instance_delete(instance=INSTANCE_ID_1,
                                             deleted_at=delete_decimal,
                                             raw=raw) \
            .AndReturn(delete)
        views.STACKDB.save(delete)
        self.mox.ReplayAll()

        views._process_delete(raw, notif[1])
        self.assertEqual(delete.instance, INSTANCE_ID_1)
        self.assertEqual(delete.deleted_at, delete_decimal)
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
        launched_range = (launch_decimal, launch_decimal+1)
        views.STACKDB.get_instance_usage(instance=INSTANCE_ID_1,
                                         launched_at__range=launched_range)\
                     .AndReturn(usage)
        views.STACKDB.get_instance_delete(instance=INSTANCE_ID_1,
                                          launched_at__range=launched_range)\
             .AndReturn(None)
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
        views._process_exists(raw, notif[1])
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
            'instance_type_id': '1',
            'usage': usage,
            'delete': delete,
            'raw': raw,
        }
        exists = self.mox.CreateMockAnything()
        views.STACKDB.create_instance_exists(**exists_values).AndReturn(exists)
        views.STACKDB.save(exists)
        self.mox.ReplayAll()
        views._process_exists(raw, notif[1])
        self.mox.VerifyAll()

