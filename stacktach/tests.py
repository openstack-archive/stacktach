import datetime
import decimal
import time

from django.utils import unittest

import datetime_to_decimal
from models import *
import views

INSTANCE_ID_1 = 'testinstanceid1'
INSTANCE_ID_2 = 'testinstanceid2'

REQUEST_ID_1 = 'testrequestid1'
REQUEST_ID_2 = 'testrequestid2'


class DatetimeToDecimalTestCase(unittest.TestCase):

    def test_datetime_to_and_from_decimal(self):
        now = datetime.datetime.utcnow()
        d = datetime_to_decimal.dt_to_decimal(now)
        daittyme = datetime_to_decimal.dt_from_decimal(d)
        self.assertEqual(now, daittyme)

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


class ViewsUtilsTestCase(unittest.TestCase):

    def test_srt_time_to_unix(self):
        unix = views.str_time_to_unix('2012-12-21 12:34:56.123')
        self.assertEqual(unix, decimal.Decimal('1356093296.123'))


class ViewsLifecycleTestCase(unittest.TestCase):

    def setUp(self):
        self.deployment = Deployment(name='TestDeployment')
        self.deployment.save()
        when1 = views.str_time_to_unix('2012-12-21 12:34:50.123')
        when2 = views.str_time_to_unix('2012-12-21 12:34:56.123')
        when3 = views.str_time_to_unix('2012-12-21 12:36:56.124')
        self.update_raw = self.create_raw(self.deployment, when1,
                                          'compute.instance.update',
                                          host='api')
        self.start_raw = self.create_raw(self.deployment, when2,
                                         'compute.instance.reboot.start')
        self.end_raw = self.create_raw(self.deployment, when3,
                                       'compute.instance.reboot.end',
                                       old_task='reboot')

    def create_raw(self, deployment, when, event, instance=INSTANCE_ID_1,
                request_id=REQUEST_ID_1, state='active', old_task='',
                host='compute'):
        raw_values  = {
            'deployment': deployment,
            'host': host,
            'state': state,
            'old_task': old_task,
            'when': when,
            'event': event,
            'instance': instance,
            'request_id': request_id,
            }
        raw = RawData(**raw_values)
        raw.save()
        return raw

    def tearDown(self):
        Deployment.objects.all().delete()
        RawData.objects.all().delete()
        Lifecycle.objects.all().delete()
        Timing.objects.all().delete()
        RequestTracker.objects.all().delete()


    def assertOnLifecycle(self, lifecycle, instance, last_raw):
        self.assertEqual(lifecycle.instance, instance)
        self.assertEqual(lifecycle.last_raw.id, last_raw.id)
        self.assertEqual(lifecycle.last_state, last_raw.state)
        self.assertEqual(lifecycle.last_task_state, last_raw.old_task)

    def assertOnTiming(self, timing, lifecycle, start_raw, end_raw, diff):
        self.assertEqual(timing.lifecycle.id, lifecycle.id)
        self.assertEqual(timing.start_raw.id, start_raw.id)
        self.assertEqual(timing.end_raw.id, end_raw.id)
        self.assertEqual(timing.start_when, start_raw.when)
        self.assertEqual(timing.end_when, end_raw.when)
        self.assertEqual(timing.diff, decimal.Decimal(diff))

    def assertOnTracker(self, tracker, request_id, lifecycle, start, diff=None):
        self.assertEqual(tracker.request_id, request_id)
        self.assertEqual(tracker.lifecycle.id, lifecycle.id)
        self.assertEqual(tracker.start, start)
        if diff:
            self.assertEqual(tracker.duration, diff)

    def test_aggregate_lifecycle_and_timing(self):
        views.aggregate_lifecycle(self.update_raw)
        views.aggregate_lifecycle(self.start_raw)

        lifecycles = Lifecycle.objects.select_related()\
                                      .filter(instance=INSTANCE_ID_1)
        self.assertEqual(len(lifecycles), 1)
        lifecycle = lifecycles[0]
        self.assertOnLifecycle(lifecycle, INSTANCE_ID_1, self.start_raw)

        views.aggregate_lifecycle(self.end_raw)

        lifecycles = Lifecycle.objects.select_related()\
                                      .filter(instance=INSTANCE_ID_1)
        self.assertEqual(len(lifecycles), 1)
        lifecycle = lifecycles[0]
        self.assertOnLifecycle(lifecycle, INSTANCE_ID_1, self.end_raw)

        timings = Timing.objects.select_related()\
                                .filter(lifecycle=lifecycle)
        self.assertEqual(len(lifecycles), 1)
        timing = timings[0]
        expected_diff = self.end_raw.when - self.start_raw.when
        self.assertOnTiming(timing, lifecycle, self.start_raw, self.end_raw,
                            expected_diff)

    def test_multiple_instance_lifecycles(self):
        when1 = views.str_time_to_unix('2012-12-21 13:32:50.123')
        when2 = views.str_time_to_unix('2012-12-21 13:34:50.123')
        when3 = views.str_time_to_unix('2012-12-21 13:37:50.124')
        update_raw2 = self.create_raw(self.deployment, when1,
                                      'compute.instance.update',
                                      instance=INSTANCE_ID_2,
                                      request_id=REQUEST_ID_2,
                                      host='api')
        start_raw2 = self.create_raw(self.deployment, when2,
                                     'compute.instance.resize.start',
                                     instance=INSTANCE_ID_2,
                                     request_id=REQUEST_ID_2)
        end_raw2 = self.create_raw(self.deployment, when3,
                                   'compute.instance.resize.end',
                                   old_task='resize',
                                   instance=INSTANCE_ID_2,
                                   request_id=REQUEST_ID_2)

        views.aggregate_lifecycle(self.update_raw)
        views.aggregate_lifecycle(self.start_raw)
        views.aggregate_lifecycle(update_raw2)
        views.aggregate_lifecycle(start_raw2)

        lifecycles = Lifecycle.objects.all().order_by('id')
        self.assertEqual(len(lifecycles), 2)
        lifecycle1 = lifecycles[0]
        self.assertOnLifecycle(lifecycle1, INSTANCE_ID_1, self.start_raw)
        lifecycle2 = lifecycles[1]
        self.assertOnLifecycle(lifecycle2, INSTANCE_ID_2, start_raw2)

        views.aggregate_lifecycle(end_raw2)
        views.aggregate_lifecycle(self.end_raw)

        lifecycles = Lifecycle.objects.all().order_by('id')
        self.assertEqual(len(lifecycles), 2)
        lifecycle1 = lifecycles[0]
        self.assertOnLifecycle(lifecycle1, INSTANCE_ID_1, self.end_raw)
        lifecycle2 = lifecycles[1]
        self.assertOnLifecycle(lifecycle2, INSTANCE_ID_2, end_raw2)

        timings = Timing.objects.all().order_by('id')
        self.assertEqual(len(timings), 2)
        timing1 = timings[0]
        expected_diff1 = self.end_raw.when - self.start_raw.when
        self.assertOnTiming(timing1, lifecycle1, self.start_raw, self.end_raw,
                            expected_diff1)
        expected_diff2 = end_raw2.when - start_raw2.when
        timing2 = timings[1]
        self.assertOnTiming(timing2, lifecycle2, start_raw2, end_raw2,
            expected_diff2)


    def test_same_instance_multiple_timings(self):
        when1 = views.str_time_to_unix('2012-12-21 13:32:50.123')
        when2 = views.str_time_to_unix('2012-12-21 13:34:50.123')
        when3 = views.str_time_to_unix('2012-12-21 13:37:50.124')
        update_raw2 = self.create_raw(self.deployment, when1,
                                      'compute.instance.update',
                                      request_id=REQUEST_ID_2,
                                      host='api')
        start_raw2 = self.create_raw(self.deployment, when2,
                                     'compute.instance.resize.start',
                                     request_id=REQUEST_ID_2)
        end_raw2 = self.create_raw(self.deployment, when3,
                                   'compute.instance.resize.end',
                                   old_task='resize',
                                   request_id=REQUEST_ID_2)

        # First action started
        views.aggregate_lifecycle(self.update_raw)
        views.aggregate_lifecycle(self.start_raw)
        # Second action started, first end is late
        views.aggregate_lifecycle(update_raw2)
        views.aggregate_lifecycle(start_raw2)
        # Finally get first end
        views.aggregate_lifecycle(self.end_raw)
        # Second end
        views.aggregate_lifecycle(end_raw2)

        lifecycles = Lifecycle.objects.select_related()\
                                      .filter(instance=INSTANCE_ID_1)
        self.assertEqual(len(lifecycles), 1)
        lifecycle1 = lifecycles[0]
        self.assertOnLifecycle(lifecycle1, INSTANCE_ID_1, end_raw2)

        timings = Timing.objects.all().order_by('id')
        self.assertEqual(len(timings), 2)
        timing1 = timings[0]
        expected_diff1 = self.end_raw.when - self.start_raw.when
        self.assertOnTiming(timing1, lifecycle1, self.start_raw, self.end_raw,
                            expected_diff1)
        expected_diff2 = end_raw2.when - start_raw2.when
        timing2 = timings[1]
        self.assertOnTiming(timing2, lifecycle1, start_raw2, end_raw2,
                            expected_diff2)

    def test_aggregate_lifecycle_and_kpi(self):
        views.aggregate_lifecycle(self.update_raw)

        lifecycles = Lifecycle.objects.select_related()\
                                      .filter(instance=INSTANCE_ID_1)
        self.assertEqual(len(lifecycles), 1)
        lifecycle = lifecycles[0]
        self.assertOnLifecycle(lifecycle, INSTANCE_ID_1, self.update_raw)

        trackers = RequestTracker.objects.filter(request_id=REQUEST_ID_1)
        self.assertEqual(len(trackers), 1)
        tracker = trackers[0]
        self.assertOnTracker(tracker, REQUEST_ID_1, lifecycle,
                             self.update_raw.when)

        views.aggregate_lifecycle(self.start_raw)
        views.aggregate_lifecycle(self.end_raw)

        trackers = RequestTracker.objects.filter(request_id=REQUEST_ID_1)
        self.assertEqual(len(trackers), 1)
        tracker = trackers[0]
        expected_diff = self.end_raw.when-self.update_raw.when
        self.assertOnTracker(tracker, REQUEST_ID_1, lifecycle,
                             self.update_raw.when, expected_diff)

    def test_multiple_instance_kpi(self):
        when1 = views.str_time_to_unix('2012-12-21 13:32:50.123')
        when2 = views.str_time_to_unix('2012-12-21 13:34:50.123')
        when3 = views.str_time_to_unix('2012-12-21 13:37:50.124')
        update_raw2 = self.create_raw(self.deployment, when1,
                                      'compute.instance.update',
                                      instance=INSTANCE_ID_2,
                                      request_id=REQUEST_ID_2,
                                      host='api')
        start_raw2 = self.create_raw(self.deployment, when2,
                                     'compute.instance.resize.start',
                                     instance=INSTANCE_ID_2,
                                     request_id=REQUEST_ID_2)
        end_raw2 = self.create_raw(self.deployment, when3,
                                   'compute.instance.resize.end',
                                   instance=INSTANCE_ID_2,
                                   old_task='resize',
                                   request_id=REQUEST_ID_2)

        views.aggregate_lifecycle(self.update_raw)
        views.aggregate_lifecycle(self.start_raw)
        views.aggregate_lifecycle(self.end_raw)
        views.aggregate_lifecycle(update_raw2)
        views.aggregate_lifecycle(start_raw2)
        views.aggregate_lifecycle(end_raw2)

        lifecycles = Lifecycle.objects.all().order_by('id')
        self.assertEqual(len(lifecycles), 2)
        lifecycle1 = lifecycles[0]
        self.assertOnLifecycle(lifecycle1, INSTANCE_ID_1, self.end_raw)
        lifecycle2 = lifecycles[1]
        self.assertOnLifecycle(lifecycle2, INSTANCE_ID_2, end_raw2)

        trackers = RequestTracker.objects.all().order_by('id')
        self.assertEqual(len(trackers), 2)
        tracker1 = trackers[0]
        expected_diff = self.end_raw.when-self.update_raw.when
        self.assertOnTracker(tracker1, REQUEST_ID_1, lifecycle1,
                             self.update_raw.when, expected_diff)
        tracker2 = trackers[1]
        expected_diff2 = end_raw2.when-update_raw2.when
        self.assertOnTracker(tracker2, REQUEST_ID_2, lifecycle2,
                             update_raw2.when, expected_diff2)

    def test_single_instance_multiple_kpi(self):
        when1 = views.str_time_to_unix('2012-12-21 13:32:50.123')
        when2 = views.str_time_to_unix('2012-12-21 13:34:50.123')
        when3 = views.str_time_to_unix('2012-12-21 13:37:50.124')
        update_raw2 = self.create_raw(self.deployment, when1,
            'compute.instance.update',
            request_id=REQUEST_ID_2,
            host='api')
        start_raw2 = self.create_raw(self.deployment, when2,
            'compute.instance.resize.start',
            request_id=REQUEST_ID_2)
        end_raw2 = self.create_raw(self.deployment, when3,
            'compute.instance.resize.end',
            old_task='resize',
            request_id=REQUEST_ID_2)

        views.aggregate_lifecycle(self.update_raw)
        views.aggregate_lifecycle(self.start_raw)
        views.aggregate_lifecycle(self.end_raw)
        views.aggregate_lifecycle(update_raw2)
        views.aggregate_lifecycle(start_raw2)
        views.aggregate_lifecycle(end_raw2)

        lifecycles = Lifecycle.objects.all().order_by('id')
        self.assertEqual(len(lifecycles), 1)
        lifecycle1 = lifecycles[0]
        self.assertOnLifecycle(lifecycle1, INSTANCE_ID_1, end_raw2)

        trackers = RequestTracker.objects.all().order_by('id')
        self.assertEqual(len(trackers), 2)
        tracker1 = trackers[0]
        expected_diff1 = self.end_raw.when-self.update_raw.when
        self.assertOnTracker(tracker1, REQUEST_ID_1, lifecycle1,
                             self.update_raw.when, expected_diff1)
        tracker2 = trackers[1]
        expected_diff2 = end_raw2.when-update_raw2.when
        self.assertOnTracker(tracker2, REQUEST_ID_2, lifecycle1,
                             update_raw2.when, expected_diff2)

    def test_single_instance_multiple_kpi_out_of_order(self):
        when1 = views.str_time_to_unix('2012-12-21 13:32:50.123')
        when2 = views.str_time_to_unix('2012-12-21 13:34:50.123')
        when3 = views.str_time_to_unix('2012-12-21 13:37:50.124')
        update_raw2 = self.create_raw(self.deployment, when1,
                                      'compute.instance.update',
                                      request_id=REQUEST_ID_2,
                                      host='api')
        start_raw2 = self.create_raw(self.deployment, when2,
                                     'compute.instance.resize.start',
                                     request_id=REQUEST_ID_2)
        end_raw2 = self.create_raw(self.deployment, when3,
                                   'compute.instance.resize.end',
                                   old_task='resize',
                                   request_id=REQUEST_ID_2)

        # First action started
        views.aggregate_lifecycle(self.update_raw)
        views.aggregate_lifecycle(self.start_raw)
        # Second action started, first end is late
        views.aggregate_lifecycle(update_raw2)
        views.aggregate_lifecycle(start_raw2)
        # Finally get first end
        views.aggregate_lifecycle(self.end_raw)
        # Second end
        views.aggregate_lifecycle(end_raw2)

        lifecycles = Lifecycle.objects.all().order_by('id')
        self.assertEqual(len(lifecycles), 1)
        lifecycle1 = lifecycles[0]
        self.assertOnLifecycle(lifecycle1, INSTANCE_ID_1, end_raw2)

        trackers = RequestTracker.objects.all().order_by('id')
        self.assertEqual(len(trackers), 2)
        tracker1 = trackers[0]
        expected_diff1 = self.end_raw.when-self.update_raw.when
        self.assertOnTracker(tracker1, REQUEST_ID_1, lifecycle1,
                             self.update_raw.when, expected_diff1)
        tracker2 = trackers[1]
        expected_diff2 = end_raw2.when-update_raw2.when
        self.assertOnTracker(tracker2, REQUEST_ID_2, lifecycle1,
                             update_raw2.when, expected_diff2)