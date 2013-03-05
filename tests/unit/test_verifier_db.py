import datetime
import decimal
import json
import unittest

import mox

from stacktach import datetime_to_decimal as dt
from stacktach import models
import utils
from utils import INSTANCE_ID_1
from utils import INSTANCE_ID_2
from utils import REQUEST_ID_1

from verifier import dbverifier
from verifier import AmbiguousResults
from verifier import FieldMismatch
from verifier import NotFound
from verifier import VerificationException


class VerifierTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(models, 'RawData', use_mock_anything=True)
        models.RawData.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'Deployment', use_mock_anything=True)
        models.Deployment.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'Lifecycle', use_mock_anything=True)
        models.Lifecycle.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'Timing', use_mock_anything=True)
        models.Timing.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'RequestTracker',
                                 use_mock_anything=True)
        models.RequestTracker.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'InstanceUsage',
                                 use_mock_anything=True)
        models.InstanceUsage.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'InstanceDeletes',
                                 use_mock_anything=True)
        models.InstanceDeletes.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'InstanceExists',
                                 use_mock_anything=True)
        models.InstanceExists.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'JsonReport', use_mock_anything=True)
        models.JsonReport.objects = self.mox.CreateMockAnything()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_verify_for_launch(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        exist.instance_type_id = 2
        exist.usage.launched_at = decimal.Decimal('1.1')
        exist.usage.instance_type_id = 2
        self.mox.ReplayAll()

        dbverifier._verify_for_launch(exist)
        self.mox.VerifyAll()

    def test_verify_for_launch_launched_at_in_range(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.0')
        exist.instance_type_id = 2
        exist.usage.launched_at = decimal.Decimal('1.4')
        exist.usage.instance_type_id = 2
        self.mox.ReplayAll()

        result = dbverifier._verify_for_launch(exist)
        self.assertIsNone(result)

        self.mox.VerifyAll()

    def test_verify_for_launch_launched_at_missmatch(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        exist.instance_type_id = 2
        exist.usage.launched_at = decimal.Decimal('2.1')
        exist.usage.instance_type_id = 2
        self.mox.ReplayAll()

        try:
            dbverifier._verify_for_launch(exist)
            self.fail()
        except FieldMismatch, fm:
            self.assertEqual(fm.field_name, 'launched_at')
            self.assertEqual(fm.expected, decimal.Decimal('1.1'))
            self.assertEqual(fm.actual, decimal.Decimal('2.1'))

        self.mox.VerifyAll()

    def test_verify_for_launch_instance_type_id_missmatch(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        exist.instance_type_id = 2
        exist.usage.launched_at = decimal.Decimal('1.1')
        exist.usage.instance_type_id = 3
        self.mox.ReplayAll()

        try:
            dbverifier._verify_for_launch(exist)
            self.fail()
        except FieldMismatch, fm:
            self.assertEqual(fm.field_name, 'instance_type_id')
            self.assertEqual(fm.expected, 2)
            self.assertEqual(fm.actual, 3)

        self.mox.VerifyAll()

    def test_verify_for_launch_late_usage(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = None
        exist.instance = INSTANCE_ID_1
        exist.launched_at = decimal.Decimal('1.1')
        exist.instance_type_id = 2
        results = self.mox.CreateMockAnything()
        models.InstanceUsage.objects.filter(instance=INSTANCE_ID_1)\
                                    .AndReturn(results)
        results.count().AndReturn(1)
        filters = {
            'instance': INSTANCE_ID_1,
            'launched_at__gte': decimal.Decimal('1.0'),
            'launched_at__lte': decimal.Decimal('1.999999')
        }
        models.InstanceUsage.objects.filter(**filters).AndReturn(results)
        results.count().AndReturn(1)
        usage = self.mox.CreateMockAnything()
        results.__getitem__(0).AndReturn(usage)
        usage.launched_at = decimal.Decimal('1.1')
        usage.instance_type_id = 2
        self.mox.ReplayAll()

        dbverifier._verify_for_launch(exist)
        self.mox.VerifyAll()

    def test_verify_for_launch_no_usage(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = None
        exist.instance = INSTANCE_ID_1
        exist.launched_at = decimal.Decimal('1.1')
        exist.instance_type_id = 2
        results = self.mox.CreateMockAnything()
        models.InstanceUsage.objects.filter(instance=INSTANCE_ID_1) \
            .AndReturn(results)
        results.count().AndReturn(0)
        self.mox.ReplayAll()

        try:
            dbverifier._verify_for_launch(exist)
            self.fail()
        except NotFound, nf:
            self.assertEqual(nf.object_type, 'InstanceUsage')
            self.assertEqual(nf.search_params, {'instance': INSTANCE_ID_1})

        self.mox.VerifyAll()

    def test_verify_for_launch_late_ambiguous_usage(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = None
        exist.instance = INSTANCE_ID_1
        exist.launched_at = decimal.Decimal('1.1')
        exist.instance_type_id = 2
        results = self.mox.CreateMockAnything()
        models.InstanceUsage.objects.filter(instance=INSTANCE_ID_1) \
            .AndReturn(results)
        results.count().AndReturn(1)
        filters = {
            'instance': INSTANCE_ID_1,
            'launched_at__gte': decimal.Decimal('1.0'),
            'launched_at__lte': decimal.Decimal('1.999999')
        }
        models.InstanceUsage.objects.filter(**filters).AndReturn(results)
        results.count().AndReturn(2)
        self.mox.ReplayAll()

        try:
            dbverifier._verify_for_launch(exist)
            self.fail()
        except AmbiguousResults, nf:
            self.assertEqual(nf.object_type, 'InstanceUsage')
            search_params = {'instance': INSTANCE_ID_1,
                             'launched_at': decimal.Decimal('1.1')}
            self.assertEqual(nf.search_params, search_params)

        self.mox.VerifyAll()

    def test_verify_for_delete(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = decimal.Decimal('5.1')
        exist.delete.launched_at = decimal.Decimal('1.1')
        exist.delete.deleted_at = decimal.Decimal('5.1')
        self.mox.ReplayAll()

        dbverifier._verify_for_delete(exist)
        self.mox.VerifyAll()

    def test_verify_for_delete_found_delete(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = None
        exist.instance = INSTANCE_ID_1
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = decimal.Decimal('5.1')
        filters = {
            'instance': INSTANCE_ID_1,
            'launched_at__gte': decimal.Decimal('1.0'),
            'launched_at__lte': decimal.Decimal('1.999999'),
        }
        results = self.mox.CreateMockAnything()
        models.InstanceDeletes.objects.filter(**filters).AndReturn(results)
        results.count().AndReturn(1)
        delete = self.mox.CreateMockAnything()
        delete.launched_at = decimal.Decimal('1.1')
        delete.deleted_at = decimal.Decimal('5.1')
        results.__getitem__(0).AndReturn(delete)

        self.mox.ReplayAll()

        dbverifier._verify_for_delete(exist)
        self.mox.VerifyAll()

    def test_verify_for_delete_non_delete(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = None
        exist.instance = INSTANCE_ID_1
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = None
        exist.raw = self.mox.CreateMockAnything()
        exist.raw.when = decimal.Decimal('1.1')
        filters = {
            'instance': INSTANCE_ID_1,
            'launched_at__gte': decimal.Decimal('1.0'),
            'launched_at__lte': decimal.Decimal('1.999999'),
            'deleted_at__lte': decimal.Decimal('1.1')
            }
        results = self.mox.CreateMockAnything()
        models.InstanceDeletes.objects.filter(**filters).AndReturn(results)
        results.count().AndReturn(0)

        self.mox.ReplayAll()

        dbverifier._verify_for_delete(exist)
        self.mox.VerifyAll()

    def test_verify_for_delete_non_delete_found_deletes(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = None
        exist.instance = INSTANCE_ID_1
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = None
        exist.raw = self.mox.CreateMockAnything()
        exist.raw.when = decimal.Decimal('1.1')
        filters = {
            'instance': INSTANCE_ID_1,
            'launched_at__gte': decimal.Decimal('1.0'),
            'launched_at__lte': decimal.Decimal('1.999999'),
            'deleted_at__lte': decimal.Decimal('1.1')
        }
        results = self.mox.CreateMockAnything()
        models.InstanceDeletes.objects.filter(**filters).AndReturn(results)
        results.count().AndReturn(1)

        self.mox.ReplayAll()

        try:
            dbverifier._verify_for_delete(exist)
            self.fail()
        except VerificationException, ve:
            msg = 'Found InstanceDeletes for non-delete exist'
            self.assertEqual(ve.reason, msg)

        self.mox.VerifyAll()

    def test_verify_for_delete_launched_at_mismatch(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = decimal.Decimal('5.1')
        exist.delete.launched_at = decimal.Decimal('2.1')
        exist.delete.deleted_at = decimal.Decimal('5.1')
        self.mox.ReplayAll()

        try:
            dbverifier._verify_for_delete(exist)
            self.fail()
        except FieldMismatch, fm:
            self.assertEqual(fm.field_name, 'launched_at')
            self.assertEqual(fm.expected, decimal.Decimal('1.1'))
            self.assertEqual(fm.actual, decimal.Decimal('2.1'))
        self.mox.VerifyAll()

    def test_verify_for_delete_deleted_at_mismatch(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = decimal.Decimal('5.1')
        exist.delete.launched_at = decimal.Decimal('1.1')
        exist.delete.deleted_at = decimal.Decimal('6.1')
        self.mox.ReplayAll()

        try:
            dbverifier._verify_for_delete(exist)
            self.fail()
        except FieldMismatch, fm:
            self.assertEqual(fm.field_name, 'deleted_at')
            self.assertEqual(fm.expected, decimal.Decimal('5.1'))
            self.assertEqual(fm.actual, decimal.Decimal('6.1'))
        self.mox.VerifyAll()

    def test_verify(self):
        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_launch')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_delete')
        self.mox.StubOutWithMock(dbverifier, '_mark_exists_failed')
        self.mox.StubOutWithMock(dbverifier, '_mark_exist_verified')
        dbverifier._verify_for_launch(exist)
        dbverifier._verify_for_delete(exist)
        dbverifier._mark_exist_verified(exist)
        self.mox.ReplayAll()
        dbverifier._verify(exist)
        self.mox.VerifyAll()

    def test_verify(self):
        exist = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(dbverifier, '_verify_for_launch')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_delete')
        self.mox.StubOutWithMock(dbverifier, '_mark_exists_failed')
        self.mox.StubOutWithMock(dbverifier, '_mark_exist_verified')
        dbverifier._mark_exists_failed(exist)
        self.mox.ReplayAll()
        dbverifier._verify(exist)
        self.mox.VerifyAll()

    def test_verify_launch_fail(self):
        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_launch')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_delete')
        self.mox.StubOutWithMock(dbverifier, '_mark_exists_failed')
        self.mox.StubOutWithMock(dbverifier, '_mark_exist_verified')
        verify_exception = VerificationException('test')
        dbverifier._verify_for_launch(exist).AndRaise(verify_exception)
        dbverifier._mark_exists_failed(exist)
        self.mox.ReplayAll()
        dbverifier._verify(exist)
        self.mox.VerifyAll()

    def test_verify_delete_fail(self):
        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_launch')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_delete')
        self.mox.StubOutWithMock(dbverifier, '_mark_exists_failed')
        self.mox.StubOutWithMock(dbverifier, '_mark_exist_verified')
        verify_exception = VerificationException('test')
        dbverifier._verify_for_launch(exist)
        dbverifier._verify_for_delete(exist).AndRaise(verify_exception)
        dbverifier._mark_exists_failed(exist)
        self.mox.ReplayAll()
        dbverifier._verify(exist)
        self.mox.VerifyAll()

    def test_verify_exception_during_launch(self):
        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_launch')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_delete')
        self.mox.StubOutWithMock(dbverifier, '_mark_exists_failed')
        self.mox.StubOutWithMock(dbverifier, '_mark_exist_verified')

        dbverifier._verify_for_launch(exist).AndRaise(Exception())
        dbverifier._mark_exists_failed(exist)
        self.mox.ReplayAll()
        dbverifier._verify(exist)
        self.mox.VerifyAll()

    def test_verify_exception_during_delete(self):
        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_launch')
        self.mox.StubOutWithMock(dbverifier, '_verify_for_delete')
        self.mox.StubOutWithMock(dbverifier, '_mark_exists_failed')
        self.mox.StubOutWithMock(dbverifier, '_mark_exist_verified')
        dbverifier._verify_for_launch(exist)
        dbverifier._verify_for_delete(exist).AndRaise(Exception())
        dbverifier._mark_exists_failed(exist)
        self.mox.ReplayAll()
        dbverifier._verify(exist)
        self.mox.VerifyAll()

    def test_verify_for_range(self):
        pool = self.mox.CreateMockAnything()
        when_max = datetime.datetime.utcnow()
        results = self.mox.CreateMockAnything()
        models.InstanceExists.objects.select_related().AndReturn(results)
        models.InstanceExists.PENDING = 'pending'
        models.InstanceExists.VERIFYING = 'verifying'
        filters = {
            'raw__when__lte': dt.dt_to_decimal(when_max),
            'status': 'pending'
        }
        results.filter(**filters).AndReturn(results)
        results.order_by('id').AndReturn(results)
        results.count().AndReturn(2)
        exist1 = self.mox.CreateMockAnything()
        exist2 = self.mox.CreateMockAnything()
        results.__iter__().AndReturn([exist1, exist2].__iter__())
        exist1.save()
        exist2.save()
        pool.apply_async(dbverifier._verify, args=(exist1,))
        pool.apply_async(dbverifier._verify, args=(exist2,))
        self.mox.ReplayAll()
        dbverifier.verify_for_range(pool, when_max)
        self.assertEqual(exist1.status, 'verifying')
        self.assertEqual(exist2.status, 'verifying')
        self.mox.VerifyAll()
