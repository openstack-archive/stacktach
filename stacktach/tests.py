import datetime
import decimal

from django.utils import unittest

import datetime_to_decimal
from models import *
import test_utils
from test_utils import INSTANCE_ID_1
from test_utils import INSTANCE_ID_2
from test_utils import MESSAGE_ID_1
from test_utils import MESSAGE_ID_2
from test_utils import REQUEST_ID_1
from test_utils import REQUEST_ID_2
from test_utils import REQUEST_ID_3
from test_utils import create_raw
import views


class ViewsUtilsTestCase(unittest.TestCase):

    def test_srt_time_to_unix(self):
        unix = views.str_time_to_unix('2012-12-21 12:34:56.123')
        self.assertEqual(unix, decimal.Decimal('1356093296.123'))


class ViewsLifecycleWorkflowTestCase(unittest.TestCase):

    def setUp(self):
        self.deployment = Deployment(name='TestDeployment')
        self.deployment.save()

        when1 = views.str_time_to_unix('2012-12-21 12:34:50.123')
        when2 = views.str_time_to_unix('2012-12-21 12:34:56.123')
        when3 = views.str_time_to_unix('2012-12-21 12:36:56.124')
        self.update_raw = create_raw(self.deployment, when1,
                                          'compute.instance.update',
                                          host='api')
        self.start_raw = create_raw(self.deployment, when2,
                                         'compute.instance.reboot.start')
        self.end_raw = create_raw(self.deployment, when3,
                                       'compute.instance.reboot.end',
                                       old_task='reboot')

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
        update_raw2 = create_raw(self.deployment, when1,
                                      'compute.instance.update',
                                      instance=INSTANCE_ID_2,
                                      request_id=REQUEST_ID_2,
                                      host='api')
        start_raw2 = create_raw(self.deployment, when2,
                                     'compute.instance.resize.start',
                                     instance=INSTANCE_ID_2,
                                     request_id=REQUEST_ID_2)
        end_raw2 = create_raw(self.deployment, when3,
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
        update_raw2 = create_raw(self.deployment, when1,
                                      'compute.instance.update',
                                      request_id=REQUEST_ID_2,
                                      host='api')
        start_raw2 = create_raw(self.deployment, when2,
                                     'compute.instance.resize.start',
                                     request_id=REQUEST_ID_2)
        end_raw2 = create_raw(self.deployment, when3,
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
        update_raw2 = create_raw(self.deployment, when1,
                                      'compute.instance.update',
                                      instance=INSTANCE_ID_2,
                                      request_id=REQUEST_ID_2,
                                      host='api')
        start_raw2 = create_raw(self.deployment, when2,
                                     'compute.instance.resize.start',
                                     instance=INSTANCE_ID_2,
                                     request_id=REQUEST_ID_2)
        end_raw2 = create_raw(self.deployment, when3,
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
        update_raw2 = create_raw(self.deployment, when1,
            'compute.instance.update',
            request_id=REQUEST_ID_2,
            host='api')
        start_raw2 = create_raw(self.deployment, when2,
            'compute.instance.resize.start',
            request_id=REQUEST_ID_2)
        end_raw2 = create_raw(self.deployment, when3,
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
        update_raw2 = create_raw(self.deployment, when1,
                                      'compute.instance.update',
                                      request_id=REQUEST_ID_2,
                                      host='api')
        start_raw2 = create_raw(self.deployment, when2,
                                     'compute.instance.resize.start',
                                     request_id=REQUEST_ID_2)
        end_raw2 = create_raw(self.deployment, when3,
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


class ViewsUsageTestCase(unittest.TestCase):
    def setUp(self):
        self.deployment = Deployment(name='TestDeployment')
        self.deployment.save()

    def tearDown(self):
        RawData.objects.all().delete()
        InstanceUsage.objects.all().delete()
        InstanceExists.objects.all().delete()

    def test_process_new_launch_create_start(self):
        when = views.str_time_to_unix('2012-12-21 12:34:50.123')
        json = test_utils.make_create_start_json()
        raw = create_raw(self.deployment, when,
                         views.INSTANCE_EVENT['create_start'], json=json)

        views._process_usage_for_new_launch(raw)

        usages = InstanceUsage.objects.all()
        self.assertEqual(len(usages), 1)
        usage = usages[0]
        self.assertEqual(usage.instance, INSTANCE_ID_1)
        self.assertEqual(usage.instance_type_id, '1')
        self.assertEqual(usage.request_id, REQUEST_ID_1)

    def test_process_new_launch_resize_prep_start(self):
        when = views.str_time_to_unix('2012-12-21 12:34:50.123')
        json = test_utils.make_resize_prep_start_json()
        raw = create_raw(self.deployment, when,
                         views.INSTANCE_EVENT['resize_prep_start'], json=json)

        views._process_usage_for_new_launch(raw)

        usages = InstanceUsage.objects.all()
        self.assertEqual(len(usages), 1)
        usage = usages[0]
        self.assertEqual(usage.instance, INSTANCE_ID_1)
        self.assertEqual(usage.request_id, REQUEST_ID_1)
        # The instance_type_id from resize prep notifications is the old one,
        #       thus we ignore it.
        self.assertIsNone(usage.instance_type_id)

    def test_process_new_launch_resize_revert_start(self):
        when = views.str_time_to_unix('2012-12-21 12:34:50.123')
        json = test_utils.make_resize_revert_start_json()
        raw = create_raw(self.deployment, when,
                         views.INSTANCE_EVENT['resize_revert_start'],
                         json=json)

        views._process_usage_for_new_launch(raw)

        usages = InstanceUsage.objects.all()
        self.assertEqual(len(usages), 1)
        usage = usages[0]
        self.assertEqual(usage.instance, INSTANCE_ID_1)
        self.assertEqual(usage.request_id, REQUEST_ID_1)
        # The instance_type_id from resize revert notifications is the old one,
        #       thus we ignore it.
        self.assertIsNone(usage.instance_type_id)

    def test_process_updates_create_end(self):
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            'instance_type_id': '1',
        }
        InstanceUsage(**values).save()

        sent = '2012-12-21 12:34:50.123'
        when = views.str_time_to_unix(sent)
        json = test_utils.make_create_end_json(sent)
        raw = create_raw(self.deployment, when,
                         views.INSTANCE_EVENT['create_end'], json=json)

        views._process_usage_for_updates(raw)

        usages = InstanceUsage.objects.all()
        self.assertEqual(len(usages), 1)
        usage = usages[0]
        self.assertEqual(usage.launched_at, when)

    def test_process_updates_resize_finish_end(self):
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            'instance_type_id': '2',
            }
        InstanceUsage(**values).save()

        sent = '2012-12-21 12:34:50.123'
        when = views.str_time_to_unix(sent)
        json = test_utils.make_resize_finish_json(sent)
        raw = create_raw(self.deployment, when,
                         views.INSTANCE_EVENT['resize_finish_end'], json=json)

        views._process_usage_for_updates(raw)

        usages = InstanceUsage.objects.all()
        self.assertEqual(len(usages), 1)
        usage = usages[0]
        self.assertEqual(usage.launched_at, when)

    def test_process_updates_revert_end(self):
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            }
        InstanceUsage(**values).save()

        sent = '2012-12-21 12:34:50.123'
        when = views.str_time_to_unix(sent)
        json = test_utils.make_resize_revert_end_json(sent)
        raw = create_raw(self.deployment, when,
                         views.INSTANCE_EVENT['resize_revert_end'], json=json)

        views._process_usage_for_updates(raw)

        usages = InstanceUsage.objects.all()
        self.assertEqual(len(usages), 1)
        usage = usages[0]
        self.assertEqual(usage.launched_at, when)
        self.assertEqual(usage.instance_type_id, '1')

    def test_process_updates_resize_prep_end(self):
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            }
        InstanceUsage(**values).save()

        sent = '2012-12-21 12:34:50.123'
        when = views.str_time_to_unix(sent)
        json = test_utils.make_resize_prep_end_json(sent)
        raw = create_raw(self.deployment, when,
                         views.INSTANCE_EVENT['resize_prep_end'], json=json)

        views._process_usage_for_updates(raw)

        usages = InstanceUsage.objects.all()
        self.assertEqual(len(usages), 1)
        usage = usages[0]
        self.assertEqual(usage.instance_type_id, '2')

    def test_process_delete(self):
        launched_str = '2012-12-21 06:34:50.123'
        launched = views.str_time_to_unix(launched_str)
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            'instance_type_id': '1',
            'launched_at': launched,
            }
        InstanceUsage(**values).save()

        deleted_str = '2012-12-21 12:34:50.123'
        deleted = views.str_time_to_unix(deleted_str)
        json = test_utils.make_delete_end_json(launched_str, deleted_str)
        raw = create_raw(self.deployment, deleted,
                         views.INSTANCE_EVENT['delete_end'], json=json)

        views._process_delete(raw)

        usages = InstanceUsage.objects.all()
        self.assertEqual(len(usages), 1)
        usage = usages[0]
        self.assertEqual(usage.deleted_at, deleted)

    def test_process_exists(self):
        launched_str = '2012-12-21 06:34:50.123'
        launched = views.str_time_to_unix(launched_str)
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            'instance_type_id': '1',
            'launched_at': launched,
            }
        InstanceUsage(**values).save()

        exists_str = '2012-12-21 23:30:00.000'
        exists_time = views.str_time_to_unix(exists_str)
        json = test_utils.make_exists_json(launched_str)
        raw = create_raw(self.deployment, exists_time,
                         views.INSTANCE_EVENT['exists'], json=json)

        views._process_exists(raw)

        usage = InstanceExists.objects.filter(instance=INSTANCE_ID_1,
                                              launched_at = launched)[0]
        exists_rows = InstanceExists.objects.all()
        self.assertEqual(len(exists_rows), 1)
        exists = exists_rows[0]
        self.assertEqual(exists.instance, INSTANCE_ID_1)
        self.assertEqual(exists.launched_at, launched)
        self.assertEqual(exists.status, InstanceExists.PENDING)
        self.assertEqual(exists.usage.id, usage.id)
        self.assertEqual(exists.raw.id, raw.id)
        self.assertEqual(exists.message_id, MESSAGE_ID_1)
        self.assertIsNone(exists.deleted_at)
        self.assertEqual(exists.instance_type_id, '1')

    def test_process_exists_with_deleted_at(self):
        launched_str = '2012-12-21 06:34:50.123'
        launched = views.str_time_to_unix(launched_str)
        deleted_str = '2012-12-21 06:36:50.123'
        deleted = views.str_time_to_unix(deleted_str)
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            'instance_type_id': '1',
            'launched_at': launched,
            'deleted_at': deleted,
            }
        InstanceUsage(**values).save()

        exists_str = '2012-12-21 23:30:00.000'
        exists_time = views.str_time_to_unix(exists_str)
        json = test_utils.make_exists_json(launched_str, deleted_at=deleted_str)
        raw = create_raw(self.deployment, exists_time,
            views.INSTANCE_EVENT['exists'], json=json)

        views._process_exists(raw)

        usage = InstanceExists.objects.filter(instance=INSTANCE_ID_1,
            launched_at = launched)[0]
        exists_rows = InstanceExists.objects.all()
        self.assertEqual(len(exists_rows), 1)
        exists = exists_rows[0]
        self.assertEqual(exists.instance, INSTANCE_ID_1)
        self.assertEqual(exists.launched_at, launched)
        self.assertEqual(exists.status, InstanceExists.PENDING)
        self.assertEqual(exists.usage.id, usage.id)
        self.assertEqual(exists.raw.id, raw.id)
        self.assertEqual(exists.message_id, MESSAGE_ID_1)
        self.assertEqual(exists.deleted_at, deleted)
        self.assertEqual(exists.instance_type_id, '1')


class ViewsUsageWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.deployment = Deployment(name='TestDeployment')
        self.deployment.save()

    def tearDown(self):
        RawData.objects.all().delete()
        InstanceUsage.objects.all().delete()
        InstanceExists.objects.all().delete()

    def assertOnUsage(self, usage, instance, type_id, launched, request_id):
        self.assertEqual(usage.instance, instance)
        self.assertEqual(usage.instance_type_id, type_id)
        self.assertEqual(usage.launched_at, launched)
        self.assertEqual(usage.request_id, request_id)

    def test_create_workflow(self):
        created_str = '2012-12-21 06:30:50.123'
        created = views.str_time_to_unix(created_str)
        launched_str = '2012-12-21 06:34:50.123'
        launched = views.str_time_to_unix(launched_str)
        create_start_json = test_utils.make_create_start_json()
        create_end_json = test_utils.make_create_end_json(launched_str)
        create_start_raw = create_raw(self.deployment, created,
                                      views.INSTANCE_EVENT['create_start'],
                                      json=create_start_json)
        create_end_raw = create_raw(self.deployment, launched,
                                    views.INSTANCE_EVENT['create_end'],
                                    json=create_end_json)

        views.aggregate_usage(create_start_raw)
        views.aggregate_usage(create_end_raw)

        usages = InstanceUsage.objects.all()
        self.assertEqual(len(usages), 1)
        usage = usages[0]
        self.assertOnUsage(usage, INSTANCE_ID_1, '1', launched, REQUEST_ID_1)

    @unittest.skip("can't handle late starts yet")
    def test_create_workflow_start_late(self):
        created_str = '2012-12-21 06:30:50.123'
        created = views.str_time_to_unix(created_str)
        launched_str = '2012-12-21 06:34:50.123'
        launched = views.str_time_to_unix(launched_str)
        create_start_json = test_utils.make_create_start_json()
        create_end_json = test_utils.make_create_end_json(launched_str)
        create_start_raw = create_raw(self.deployment, created,
                                      views.INSTANCE_EVENT['create_start'],
                                      json=create_start_json)
        create_end_raw = create_raw(self.deployment, launched,
                                    views.INSTANCE_EVENT['create_end'],
                                    json=create_end_json)

        views.aggregate_usage(create_end_raw)
        views.aggregate_usage(create_start_raw)

        usages = InstanceUsage.objects.all()
        self.assertEqual(len(usages), 1)
        usage = usages[0]
        self.assertOnUsage(usage, INSTANCE_ID_1, '1', launched, REQUEST_ID_1)

    def test_resize_workflow(self):
        launched_str = '2012-12-21 06:34:50.123'
        launched = views.str_time_to_unix(launched_str)
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            'instance_type_id': '1',
            'launched_at': launched,
            }
        InstanceUsage(**values).save()

        started_str = '2012-12-22 06:34:50.123'
        started_time = views.str_time_to_unix(started_str)
        pre_end_str = '2012-12-22 06:36:50.123'
        prep_end_time = views.str_time_to_unix(pre_end_str)
        finish_str = '2012-12-22 06:38:50.123'
        finish_time = views.str_time_to_unix(finish_str)
        prep_start_json = test_utils\
                          .make_resize_prep_start_json(request_id=REQUEST_ID_2)
        prep_end_json = test_utils\
                        .make_resize_prep_end_json(new_instance_type_id='2',
                                                   request_id=REQUEST_ID_2)
        finish_json = test_utils\
                      .make_resize_finish_json(launched_at=finish_str,
                                               request_id=REQUEST_ID_2)
        prep_start_raw = create_raw(self.deployment, started_time,
                                    views.INSTANCE_EVENT['resize_prep_start'],
                                    request_id=REQUEST_ID_2,
                                    json=prep_start_json)
        prep_end_raw = create_raw(self.deployment, prep_end_time,
                                  views.INSTANCE_EVENT['resize_prep_end'],
                                  request_id=REQUEST_ID_2,
                                  json=prep_end_json)
        finish_raw = create_raw(self.deployment, finish_time,
                                views.INSTANCE_EVENT['resize_finish_end'],
                                request_id=REQUEST_ID_2,
                                json=finish_json)

        views.aggregate_usage(prep_start_raw)
        views.aggregate_usage(prep_end_raw)
        views.aggregate_usage(finish_raw)

        usages = InstanceUsage.objects.all().order_by('id')
        self.assertEqual(len(usages), 2)
        usage_before = usages[0]
        usage_after = usages[1]
        self.assertOnUsage(usage_before, INSTANCE_ID_1, '1', launched,
                           REQUEST_ID_1)
        self.assertOnUsage(usage_after, INSTANCE_ID_1, '2', finish_time,
                           REQUEST_ID_2)

    def test_resize_workflow_out_of_order(self):
        launched_str = '2012-12-21 06:34:50.123'
        launched = views.str_time_to_unix(launched_str)
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            'instance_type_id': '1',
            'launched_at': launched,
            }
        InstanceUsage(**values).save()

        started_str = '2012-12-22 06:34:50.123'
        started_time = views.str_time_to_unix(started_str)
        pre_end_str = '2012-12-22 06:36:50.123'
        prep_end_time = views.str_time_to_unix(pre_end_str)
        finish_str = '2012-12-22 06:38:50.123'
        finish_time = views.str_time_to_unix(finish_str)
        prep_start_json = test_utils\
        .make_resize_prep_start_json(request_id=REQUEST_ID_2)
        prep_end_json = test_utils\
                        .make_resize_prep_end_json(new_instance_type_id='2',
                                                   request_id=REQUEST_ID_2)
        finish_json = test_utils\
                      .make_resize_finish_json(launched_at=finish_str,
                                               request_id=REQUEST_ID_2)
        prep_start_raw = create_raw(self.deployment, started_time,
                                    views.INSTANCE_EVENT['resize_prep_start'],
                                    request_id=REQUEST_ID_2,
                                    json=prep_start_json)
        prep_end_raw = create_raw(self.deployment, prep_end_time,
                                  views.INSTANCE_EVENT['resize_prep_end'],
                                  request_id=REQUEST_ID_2,
                                  json=prep_end_json)
        finish_raw = create_raw(self.deployment, finish_time,
                                views.INSTANCE_EVENT['resize_finish_end'],
                                request_id=REQUEST_ID_2,
                                json=finish_json)

        # Resize Started, notification on time
        views.aggregate_usage(prep_start_raw)
        # Received finish_end, prep_end late
        views.aggregate_usage(finish_raw)
        # Finally receive the late prep_end
        views.aggregate_usage(prep_end_raw)

        usages = InstanceUsage.objects.all().order_by('id')
        self.assertEqual(len(usages), 2)
        usage_before = usages[0]
        usage_after = usages[1]
        self.assertOnUsage(usage_before, INSTANCE_ID_1, '1', launched,
                           REQUEST_ID_1)
        self.assertOnUsage(usage_after, INSTANCE_ID_1, '2', finish_time,
                           REQUEST_ID_2)

    @unittest.skip("can't handle late starts yet")
    def test_resize_workflow_start_late(self):
        launched_str = '2012-12-21 06:34:50.123'
        launched = views.str_time_to_unix(launched_str)
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            'instance_type_id': '1',
            'launched_at': launched,
            }
        InstanceUsage(**values).save()

        started_str = '2012-12-22 06:34:50.123'
        started_time = views.str_time_to_unix(started_str)
        pre_end_str = '2012-12-22 06:36:50.123'
        prep_end_time = views.str_time_to_unix(pre_end_str)
        finish_str = '2012-12-22 06:38:50.123'
        finish_time = views.str_time_to_unix(finish_str)
        prep_start_json = test_utils\
        .make_resize_prep_start_json(request_id=REQUEST_ID_2)
        prep_end_json = test_utils\
                        .make_resize_prep_end_json(new_instance_type_id='2',
                                                   request_id=REQUEST_ID_2)
        finish_json = test_utils\
                      .make_resize_finish_json(launched_at=finish_str,
                                               request_id=REQUEST_ID_2)
        prep_start_raw = create_raw(self.deployment, started_time,
                                    views.INSTANCE_EVENT['resize_prep_start'],
                                    request_id=REQUEST_ID_2,
                                    json=prep_start_json)
        prep_end_raw = create_raw(self.deployment, prep_end_time,
                                  views.INSTANCE_EVENT['resize_prep_end'],
                                  request_id=REQUEST_ID_2,
                                  json=prep_end_json)
        finish_raw = create_raw(self.deployment, finish_time,
                                views.INSTANCE_EVENT['resize_finish_end'],
                                request_id=REQUEST_ID_2,
                                json=finish_json)

        views.aggregate_usage(prep_end_raw)
        views.aggregate_usage(prep_start_raw)
        views.aggregate_usage(finish_raw)

        usages = InstanceUsage.objects.all().order_by('id')
        self.assertEqual(len(usages), 2)
        usage_before = usages[0]
        usage_after = usages[1]
        self.assertOnUsage(usage_before, INSTANCE_ID_1, '1', launched,
                           REQUEST_ID_1)
        self.assertOnUsage(usage_after, INSTANCE_ID_1, '2', finish_time,
                           REQUEST_ID_2)

    def test_resize_revert_workflow(self):
        launched_str = '2012-12-21 06:34:50.123'
        launched = views.str_time_to_unix(launched_str)
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            'instance_type_id': '1',
            'launched_at': launched,
            }
        InstanceUsage(**values).save()
        resize_launched_str = '2012-12-22 06:34:50.123'
        resize_launched = views.str_time_to_unix(resize_launched_str)
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_2,
            'instance_type_id': '2',
            'launched_at': resize_launched,
            }
        InstanceUsage(**values).save()

        started_str = '2012-12-22 06:34:50.123'
        started_time = views.str_time_to_unix(started_str)
        end_str = '2012-12-22 06:36:50.123'
        end_time = views.str_time_to_unix(end_str)
        start_json = test_utils\
                     .make_resize_revert_start_json(request_id=REQUEST_ID_3)
        end_json = test_utils\
                   .make_resize_revert_end_json(launched_at=end_str,
                                                request_id=REQUEST_ID_3)
        start_raw = create_raw(self.deployment, started_time,
                               views.INSTANCE_EVENT['resize_revert_start'],
                               request_id=REQUEST_ID_3, json=start_json)
        end_raw = create_raw(self.deployment, started_time,
                             views.INSTANCE_EVENT['resize_revert_end'],
                             request_id=REQUEST_ID_3, json=end_json)

        views.aggregate_usage(start_raw)
        views.aggregate_usage(end_raw)

        usages = InstanceUsage.objects.all().order_by('id')
        self.assertEqual(len(usages), 3)
        usage_before_resize = usages[0]
        usage_after_resize = usages[1]
        usage_after_revert = usages[2]
        self.assertOnUsage(usage_before_resize, INSTANCE_ID_1, '1', launched,
                           REQUEST_ID_1)
        self.assertOnUsage(usage_after_resize, INSTANCE_ID_1, '2',
                           resize_launched, REQUEST_ID_2)
        self.assertOnUsage(usage_after_revert, INSTANCE_ID_1, '1', end_time,
                           REQUEST_ID_3)

    @unittest.skip("can't handle late starts yet")
    def test_resize_revert_workflow_start_late(self):
        launched_str = '2012-12-21 06:34:50.123'
        launched = views.str_time_to_unix(launched_str)
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_1,
            'instance_type_id': '1',
            'launched_at': launched,
            }
        InstanceUsage(**values).save()
        resize_launched_str = '2012-12-22 06:34:50.123'
        resize_launched = views.str_time_to_unix(resize_launched_str)
        values = {
            'instance': INSTANCE_ID_1,
            'request_id': REQUEST_ID_2,
            'instance_type_id': '2',
            'launched_at': resize_launched,
            }
        InstanceUsage(**values).save()

        started_str = '2012-12-22 06:34:50.123'
        started_time = views.str_time_to_unix(started_str)
        end_str = '2012-12-22 06:36:50.123'
        end_time = views.str_time_to_unix(end_str)
        start_json = test_utils\
                     .make_resize_revert_start_json(request_id=REQUEST_ID_3)
        end_json = test_utils\
                   .make_resize_revert_end_json(launched_at=end_str,
                                                request_id=REQUEST_ID_3)
        start_raw = create_raw(self.deployment, started_time,
                               views.INSTANCE_EVENT['resize_revert_start'],
                               request_id=REQUEST_ID_3, json=start_json)
        end_raw = create_raw(self.deployment, started_time,
                             views.INSTANCE_EVENT['resize_revert_end'],
                             request_id=REQUEST_ID_3, json=end_json)

        views.aggregate_usage(end_raw)
        views.aggregate_usage(start_raw)

        usages = InstanceUsage.objects.all().order_by('id')
        self.assertEqual(len(usages), 3)
        usage_before_resize = usages[0]
        usage_after_resize = usages[1]
        usage_after_revert = usages[2]
        self.assertOnUsage(usage_before_resize, INSTANCE_ID_1, '1', launched,
                           REQUEST_ID_1)
        self.assertOnUsage(usage_after_resize, INSTANCE_ID_1, '2',
                           resize_launched, REQUEST_ID_2)
        self.assertOnUsage(usage_after_revert, INSTANCE_ID_1, '1', end_time,
                           REQUEST_ID_3)
