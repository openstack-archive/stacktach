import datetime
import os
import sys
import unittest

import mox

INSTANCE_ID_1 = 'testinstanceid1'
INSTANCE_ID_2 = 'testinstanceid2'

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path = [os.path.abspath(os.path.dirname('stacktach'))] + sys.path

from stacktach import views
import test_utils as utils

class StacktachLifecycleTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()
        views.STACKDB = self.mox.CreateMockAnything()

    def tearDown(self):
        pass

    def test_aggregate_lifecycle_no_instance(self):
        raw = self.mox.CreateMockAnything()
        raw.instance = None

        views.aggregate_lifecycle(raw)

        self.mox.ReplayAll()
        self.mox.VerifyAll()

    def test_aggregate_lifecycle_start(self):
        event_name = 'compute.instance.create'
        event = '%s.start' % event_name
        when = datetime.datetime.utcnow()
        raw = utils.create_raw(self.mox, when, event, state='building')

        views.STACKDB.find_lifecycles(instance=INSTANCE_ID_1).AndReturn([])
        lifecycle = self.mox.CreateMockAnything()
        lifecycle.instance = INSTANCE_ID_1
        views.STACKDB.create_lifecycle(instance=INSTANCE_ID_1).AndReturn(lifecycle)
        views.STACKDB.save(lifecycle)

        views.STACKDB.find_timings(name=event_name, lifecycle=lifecycle).AndReturn([])
        timing = utils.create_timing(self.mox, event_name, lifecycle)
        views.STACKDB.create_timing(lifecycle=lifecycle, name=event_name).AndReturn(timing)
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
        views.STACKDB.find_lifecycles(instance=INSTANCE_ID_1).AndReturn([lifecycle])
        views.STACKDB.save(lifecycle)

        timing = utils.create_timing(self.mox, event_name, lifecycle,
                                     start_raw=start_raw,
                                     start_when=start_when)
        views.STACKDB.find_timings(name=event_name, lifecycle=lifecycle).AndReturn([timing])

        self.mox.StubOutWithMock(views, "update_kpi")
        views.update_kpi(lifecycle, timing, end_raw)
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

        self.mox.UnsetStubs()
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

        self.mox.UnsetStubs()
        self.mox.VerifyAll()
