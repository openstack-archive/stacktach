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

import datetime
import decimal
import json
import uuid

import kombu.common
import kombu.entity
import kombu.pools
import mox

from stacktach import datetime_to_decimal as dt
from stacktach import stacklog
from stacktach import models
from tests.unit import StacktachBaseTestCase
from utils import make_verifier_config, LAUNCHED_AT_1, INSTANCE_FLAVOR_ID_1, INSTANCE_FLAVOR_ID_2, FLAVOR_FIELD_NAME, DELETED_AT_1, LAUNCHED_AT_2, DELETED_AT_2
from utils import INSTANCE_ID_1
from utils import RAX_OPTIONS_1
from utils import RAX_OPTIONS_2
from utils import OS_DISTRO_1
from utils import OS_DISTRO_2
from utils import OS_ARCH_1
from utils import OS_ARCH_2
from utils import OS_VERSION_1
from utils import OS_VERSION_2
from utils import TENANT_ID_1
from utils import TENANT_ID_2
from utils import NOVA_VERIFIER_EVENT_TYPE
from verifier import nova_verifier
from verifier import config
from verifier import NullFieldException
from verifier import WrongTypeException
from verifier import AmbiguousResults
from verifier import FieldMismatch
from verifier import NotFound
from verifier import VerificationException


class NovaVerifierVerifyForLaunchTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(models, 'InstanceUsage',
                                 use_mock_anything=True)
        models.InstanceUsage.objects = self.mox.CreateMockAnything()

        self._setup_verifier()

    def _setup_verifier(self):
        self.pool = self.mox.CreateMockAnything()
        self.reconciler = self.mox.CreateMockAnything()
        config = make_verifier_config(False)
        self.verifier = nova_verifier.NovaVerifier(config,
            pool=self.pool, reconciler=self.reconciler)

    def tearDown(self):
        self.mox.UnsetStubs()
        self.verifier = None
        self.pool = None
        self.verifier_notif = None

    def test_verify_for_launch(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn("flavor_field_name")

        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        exist.dummy_flavor_field_name = 'dummy_flavor'
        exist.tenant = TENANT_ID_1

        exist.usage = self.mox.CreateMockAnything()
        exist.usage.launched_at = decimal.Decimal('1.1')
        exist.usage.dummy_flavor_field_name = 'dummy_flavor'
        exist.usage.tenant = TENANT_ID_1
        self.mox.ReplayAll()

        nova_verifier._verify_for_launch(exist)

        self.mox.VerifyAll()

    def test_verify_for_launch_launched_at_in_range(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')
        exist = self.mox.CreateMockAnything()
        exist.usage = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.0')
        exist.dummy_flavor_field_name = 'dummy_flavor'
        exist.usage.launched_at = decimal.Decimal('1.4')
        exist.usage.dummy_flavor_field_name = 'dummy_flavor'
        self.mox.ReplayAll()

        result = nova_verifier._verify_for_launch(exist)
        self.assertIsNone(result)

        self.mox.VerifyAll()

    def test_verify_for_launch_launched_at_missmatch(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn("flavor_field_name")
        exist = self.mox.CreateMockAnything()
        exist.usage = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        exist.dummy_flavor_field_name = 'dummy_flavor'
        exist.usage.launched_at = decimal.Decimal('2.1')
        exist.usage.dummy_flavor_field_name = 'dummy_flavor'
        self.mox.ReplayAll()

        try:
            nova_verifier._verify_for_launch(exist)
            self.fail()
        except FieldMismatch, fm:
            self.assertEqual(fm.field_name, 'launched_at')
            self.assertEqual(fm.expected, decimal.Decimal('1.1'))
            self.assertEqual(fm.actual, decimal.Decimal('2.1'))

        self.mox.VerifyAll()

    def test_verify_for_launch_flavor_id_missmatch(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn(FLAVOR_FIELD_NAME)
        exist = self.mox.CreateMockAnything()
        exist.instance = INSTANCE_ID_1
        exist.usage = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal(LAUNCHED_AT_1)
        exist.flavor_field_name = INSTANCE_FLAVOR_ID_1
        exist.usage.launched_at = decimal.Decimal(LAUNCHED_AT_1)
        exist.usage.flavor_field_name = INSTANCE_FLAVOR_ID_2
        self.mox.ReplayAll()
        with self.assertRaises(FieldMismatch) as fm:
            nova_verifier._verify_for_launch(exist)
        exception = fm.exception
        self.assertEqual(exception.field_name, FLAVOR_FIELD_NAME)
        self.assertEqual(exception.expected, INSTANCE_FLAVOR_ID_1)
        self.assertEqual(exception.actual, INSTANCE_FLAVOR_ID_2)
        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for "
            "08f685d9-6352-4dbc-8271-96cc54bf14cd: Expected flavor_field_name "
            "to be '1' got 'performance2-120'")
        self.mox.VerifyAll()

    def test_verify_for_launch_tenant_id_mismatch(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn(FLAVOR_FIELD_NAME)

        exist = self.mox.CreateMockAnything()
        exist.tenant = TENANT_ID_1

        exist.usage = self.mox.CreateMockAnything()
        exist.usage.tenant = TENANT_ID_2
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as cm:
            nova_verifier._verify_for_launch(exist)
        exception = cm.exception

        self.assertEqual(exception.field_name, 'tenant')
        self.assertEqual(exception.expected, TENANT_ID_1)
        self.assertEqual(exception.actual, TENANT_ID_2)

        self.mox.VerifyAll()

    def test_verify_for_launch_rax_options_mismatch(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn("flavor_field_name")
        exist = self.mox.CreateMockAnything()
        exist.rax_options = RAX_OPTIONS_1

        exist.usage = self.mox.CreateMockAnything()
        exist.usage.rax_options = RAX_OPTIONS_2
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as cm:
            nova_verifier._verify_for_launch(exist)
        exception = cm.exception

        self.assertEqual(exception.field_name, 'rax_options')
        self.assertEqual(exception.expected, RAX_OPTIONS_1)
        self.assertEqual(exception.actual, RAX_OPTIONS_2)

        self.mox.VerifyAll()

    def test_verify_for_launch_os_distro_mismatch(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn("flavor_field_name")
        exist = self.mox.CreateMockAnything()
        exist.os_distro = OS_DISTRO_1

        exist.usage = self.mox.CreateMockAnything()
        exist.usage.os_distro = OS_DISTRO_2
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as cm:
            nova_verifier._verify_for_launch(exist)
        exception = cm.exception

        self.assertEqual(exception.field_name, 'os_distro')
        self.assertEqual(exception.expected, OS_DISTRO_1)
        self.assertEqual(exception.actual, OS_DISTRO_2)

        self.mox.VerifyAll()

    def test_verify_for_launch_os_architecture_mismatch(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn("flavor_field_name")
        exist = self.mox.CreateMockAnything()
        exist.os_architecture = OS_ARCH_1

        exist.usage = self.mox.CreateMockAnything()
        exist.usage.os_architecture = OS_ARCH_2
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as cm:
            nova_verifier._verify_for_launch(exist)
        exception = cm.exception

        self.assertEqual(exception.field_name, 'os_architecture')
        self.assertEqual(exception.expected, OS_ARCH_1)
        self.assertEqual(exception.actual, OS_ARCH_2)

        self.mox.VerifyAll()

    def test_verify_for_launch_os_version_mismatch(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn("flavor_field_name")
        exist = self.mox.CreateMockAnything()
        exist.os_version = OS_VERSION_1

        exist.usage = self.mox.CreateMockAnything()
        exist.usage.os_version = OS_VERSION_2
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as cm:
            nova_verifier._verify_for_launch(exist)
        exception = cm.exception

        self.assertEqual(exception.field_name, 'os_version')
        self.assertEqual(exception.expected, OS_VERSION_1)
        self.assertEqual(exception.actual, OS_VERSION_2)

        self.mox.VerifyAll()

    def test_verify_for_launch_late_usage(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn("flavor_field_name")
        exist = self.mox.CreateMockAnything()
        exist.usage = None
        exist.instance = INSTANCE_ID_1
        launched_at = decimal.Decimal('1.1')
        exist.launched_at = launched_at
        exist.dummy_flavor_field_name = 'dummy_flavor'
        results = self.mox.CreateMockAnything()
        models.InstanceUsage.objects.filter(instance=INSTANCE_ID_1)\
            .AndReturn(results)
        results.count().AndReturn(2)
        models.InstanceUsage.find(INSTANCE_ID_1, dt.dt_from_decimal(
            launched_at)).AndReturn(results)
        results.count().AndReturn(1)
        usage = self.mox.CreateMockAnything()
        results.__getitem__(0).AndReturn(usage)
        usage.launched_at = decimal.Decimal('1.1')
        usage.dummy_flavor_field_name = 'dummy_flavor'
        self.mox.ReplayAll()

        nova_verifier._verify_for_launch(exist)
        self.mox.VerifyAll()

    def test_verify_for_launch_no_usage(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = None
        exist.instance = INSTANCE_ID_1
        exist.launched_at = decimal.Decimal('1.1')
        exist.dummy_flavor_field_name = 'dummy_flavor'
        results = self.mox.CreateMockAnything()
        models.InstanceUsage.objects.filter(instance=INSTANCE_ID_1) \
            .AndReturn(results)
        results.count().AndReturn(0)
        self.mox.ReplayAll()

        with self.assertRaises(NotFound) as nf:
            nova_verifier._verify_for_launch(exist)
        exception = nf.exception
        self.assertEqual(exception.object_type, 'InstanceUsage')
        self.assertEqual(exception.search_params, {'instance': INSTANCE_ID_1})

        self.mox.VerifyAll()

    def test_verify_for_launch_late_ambiguous_usage(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = None
        exist.instance = INSTANCE_ID_1
        launched_at = decimal.Decimal('1.1')
        exist.launched_at = launched_at
        exist.dummy_flavor_field_name = 'dummy_flavor'
        results = self.mox.CreateMockAnything()
        models.InstanceUsage.objects.filter(
            instance=INSTANCE_ID_1).AndReturn(results)
        results.count().AndReturn(1)
        models.InstanceUsage.find(
            INSTANCE_ID_1, dt.dt_from_decimal(launched_at)).AndReturn(results)
        results.count().AndReturn(2)
        self.mox.ReplayAll()

        with self.assertRaises(AmbiguousResults) as ar:
            nova_verifier._verify_for_launch(exist)
        exception = ar.exception
        self.assertEqual(exception.object_type, 'InstanceUsage')
        search_params = {'instance': INSTANCE_ID_1,
                         'launched_at': decimal.Decimal('1.1')}
        self.assertEqual(exception.search_params, search_params)

        self.mox.VerifyAll()


class NovaVerifierVerifyForDeleteTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self._setup_verifier()
        self.mox.StubOutWithMock(models, 'InstanceDeletes',
                                 use_mock_anything=True)
        models.InstanceDeletes.objects = self.mox.CreateMockAnything()
    def _setup_verifier(self):
        self.pool = self.mox.CreateMockAnything()
        self.reconciler = self.mox.CreateMockAnything()
        config = make_verifier_config(False)
        self.verifier = nova_verifier.NovaVerifier(config,
            pool=self.pool, reconciler=self.reconciler)

    def tearDown(self):
        self.mox.UnsetStubs()
        self.verifier = None
        self.pool = None
        self.verifier_notif = None

    def test_verify_for_delete(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = decimal.Decimal('5.1')
        exist.delete.launched_at = decimal.Decimal('1.1')
        exist.delete.deleted_at = decimal.Decimal('5.1')
        self.mox.ReplayAll()

        nova_verifier._verify_for_delete(exist)
        self.mox.VerifyAll()

    def test_verify_for_delete_found_delete(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = None
        exist.instance = INSTANCE_ID_1
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = decimal.Decimal('5.1')
        launched_at = decimal.Decimal('1.1')
        results = self.mox.CreateMockAnything()
        models.InstanceDeletes.find(INSTANCE_ID_1, dt.dt_from_decimal(
                                    launched_at)).AndReturn(results)
        results.count().AndReturn(1)
        delete = self.mox.CreateMockAnything()
        delete.launched_at = decimal.Decimal('1.1')
        delete.deleted_at = decimal.Decimal('5.1')
        results.__getitem__(0).AndReturn(delete)

        self.mox.ReplayAll()

        nova_verifier._verify_for_delete(exist)
        self.mox.VerifyAll()

    def test_verify_for_delete_non_delete(self):
        launched_at = decimal.Decimal('1.1')
        deleted_at = decimal.Decimal('1.1')
        exist = self.mox.CreateMockAnything()
        exist.delete = None
        exist.instance = INSTANCE_ID_1
        exist.launched_at = launched_at
        exist.deleted_at = None
        exist.audit_period_ending = deleted_at
        results = self.mox.CreateMockAnything()
        models.InstanceDeletes.find(
            INSTANCE_ID_1, dt.dt_from_decimal(launched_at),
            dt.dt_from_decimal(deleted_at)).AndReturn(results)
        results.count().AndReturn(0)

        self.mox.ReplayAll()

        nova_verifier._verify_for_delete(exist)
        self.mox.VerifyAll()

    def test_verify_for_delete_non_delete_found_deletes(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = None
        exist.instance = INSTANCE_ID_1
        launched_at = decimal.Decimal('1.1')
        deleted_at = decimal.Decimal('1.3')
        exist.launched_at = launched_at
        exist.deleted_at = None
        exist.audit_period_ending = deleted_at
        results = self.mox.CreateMockAnything()
        models.InstanceDeletes.find(
            INSTANCE_ID_1, dt.dt_from_decimal(launched_at),
            dt.dt_from_decimal(deleted_at)).AndReturn(results)
        results.count().AndReturn(1)

        self.mox.ReplayAll()

        with self.assertRaises(VerificationException) as ve:
            nova_verifier._verify_for_delete(exist)
        exception = ve.exception
        msg = 'Found InstanceDeletes for non-delete exist'
        self.assertEqual(exception.reason, msg)

        self.mox.VerifyAll()

    def test_verify_for_delete_launched_at_mismatch(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = self.mox.CreateMockAnything()
        exist.launched_at = LAUNCHED_AT_1
        exist.deleted_at = DELETED_AT_1
        exist.delete.launched_at = LAUNCHED_AT_2
        exist.delete.deleted_at = DELETED_AT_1
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as fm:
            nova_verifier._verify_for_delete(exist)
        exception = fm.exception
        self.assertEqual(exception.field_name, 'launched_at')
        self.assertEqual(exception.expected, LAUNCHED_AT_1)
        self.assertEqual(exception.actual, LAUNCHED_AT_2)
        self.mox.VerifyAll()

    def test_verify_for_delete_deleted_at_mismatch(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = self.mox.CreateMockAnything()
        exist.launched_at = LAUNCHED_AT_1
        exist.deleted_at = DELETED_AT_1
        exist.delete.launched_at = LAUNCHED_AT_1
        exist.delete.deleted_at = DELETED_AT_2
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as fm:
            nova_verifier._verify_for_delete(exist)
        exception = fm.exception
        self.assertEqual(exception.field_name, 'deleted_at')
        self.assertEqual(exception.expected, DELETED_AT_1)
        self.assertEqual(exception.actual, DELETED_AT_2)
        self.mox.VerifyAll()


class NovaVerifierReconcileTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(models, 'InstanceReconcile',
                                 use_mock_anything=True)
        models.InstanceReconcile.objects = self.mox.CreateMockAnything()
        self._setup_verifier()

    def _setup_verifier(self):
        self.pool = self.mox.CreateMockAnything()
        self.reconciler = self.mox.CreateMockAnything()
        config = make_verifier_config(False)
        self.verifier = nova_verifier.NovaVerifier(config,
            pool=self.pool, reconciler=self.reconciler)

    def tearDown(self):
        self.mox.UnsetStubs()
        self.verifier = None
        self.pool = None
        self.verifier_notif = None

    def test_reconcile_failed(self):
        self.verifier.reconcile = True
        exists1 = self.mox.CreateMockAnything()
        exists2 = self.mox.CreateMockAnything()
        self.verifier.failed = [exists1, exists2]
        self.reconciler.failed_validation(exists1)
        self.reconciler.failed_validation(exists2)
        self.mox.ReplayAll()
        self.verifier.reconcile_failed()
        self.assertEqual(len(self.verifier.failed), 0)
        self.mox.VerifyAll()

    def test_verify_with_reconciled_data(self):
        exists = self.mox.CreateMockAnything()
        exists.instance = INSTANCE_ID_1
        launched_at = decimal.Decimal('1.1')
        exists.launched_at = launched_at
        results = self.mox.CreateMockAnything()
        models.InstanceReconcile.objects.filter(instance=INSTANCE_ID_1)\
                                        .AndReturn(results)
        results.count().AndReturn(1)
        launched_at = dt.dt_from_decimal(decimal.Decimal('1.1'))
        recs = self.mox.CreateMockAnything()
        models.InstanceReconcile.find(INSTANCE_ID_1, launched_at).AndReturn(recs)
        recs.count().AndReturn(1)
        reconcile = self.mox.CreateMockAnything()
        reconcile.deleted_at = None
        recs[0].AndReturn(reconcile)
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        nova_verifier._verify_for_launch(exists, launch=reconcile,
                                      launch_type='InstanceReconcile')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        nova_verifier._verify_for_delete(exists, delete=None,
                                      delete_type='InstanceReconcile')
        self.mox.ReplayAll()
        nova_verifier._verify_with_reconciled_data(exists)
        self.mox.VerifyAll()

    def test_verify_with_reconciled_data_deleted(self):
        exists = self.mox.CreateMockAnything()
        exists.instance = INSTANCE_ID_1
        launched_at = decimal.Decimal('1.1')
        deleted_at = decimal.Decimal('2.1')
        exists.launched_at = launched_at
        exists.deleted_at = deleted_at
        results = self.mox.CreateMockAnything()
        models.InstanceReconcile.objects.filter(instance=INSTANCE_ID_1)\
                                        .AndReturn(results)
        results.count().AndReturn(1)
        launched_at = dt.dt_from_decimal(decimal.Decimal('1.1'))
        recs = self.mox.CreateMockAnything()
        models.InstanceReconcile.find(INSTANCE_ID_1, launched_at).AndReturn(recs)
        recs.count().AndReturn(1)
        reconcile = self.mox.CreateMockAnything()
        reconcile.deleted_at = deleted_at
        recs[0].AndReturn(reconcile)
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        nova_verifier._verify_for_launch(exists, launch=reconcile,
                                      launch_type='InstanceReconcile')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        nova_verifier._verify_for_delete(exists, delete=reconcile,
                                      delete_type='InstanceReconcile')
        self.mox.ReplayAll()
        nova_verifier._verify_with_reconciled_data(exists)
        self.mox.VerifyAll()

    def test_verify_with_reconciled_data_not_launched(self):
        exists = self.mox.CreateMockAnything()
        exists.instance = INSTANCE_ID_1
        exists.launched_at = None
        self.mox.ReplayAll()
        with self.assertRaises(VerificationException) as cm:
            nova_verifier._verify_with_reconciled_data(exists)
        exception = cm.exception
        self.assertEquals(exception.reason, 'Exists without a launched_at')
        self.mox.VerifyAll()

    def test_verify_with_reconciled_data_ambiguous_results(self):
        exists = self.mox.CreateMockAnything()
        exists.instance = INSTANCE_ID_1
        launched_at = decimal.Decimal('1.1')
        deleted_at = decimal.Decimal('2.1')
        exists.launched_at = launched_at
        exists.deleted_at = deleted_at
        results = self.mox.CreateMockAnything()
        models.InstanceReconcile.objects.filter(instance=INSTANCE_ID_1)\
                                        .AndReturn(results)
        results.count().AndReturn(1)
        launched_at = dt.dt_from_decimal(decimal.Decimal('1.1'))
        recs = self.mox.CreateMockAnything()
        models.InstanceReconcile.find(INSTANCE_ID_1, launched_at).AndReturn(recs)
        recs.count().AndReturn(2)
        self.mox.ReplayAll()
        with self.assertRaises(AmbiguousResults) as cm:
            nova_verifier._verify_with_reconciled_data(exists)
        exception = cm.exception
        self.assertEquals(exception.object_type, 'InstanceReconcile')
        self.mox.VerifyAll()

    def test_verify_with_reconciled_data_instance_not_found(self):
        exists = self.mox.CreateMockAnything()
        exists.instance = INSTANCE_ID_1
        launched_at = decimal.Decimal('1.1')
        deleted_at = decimal.Decimal('2.1')
        exists.launched_at = launched_at
        exists.deleted_at = deleted_at
        results = self.mox.CreateMockAnything()
        models.InstanceReconcile.objects.filter(instance=INSTANCE_ID_1)\
                                        .AndReturn(results)
        results.count().AndReturn(0)
        self.mox.ReplayAll()
        with self.assertRaises(NotFound) as cm:
            nova_verifier._verify_with_reconciled_data(exists)
        exception = cm.exception
        self.assertEquals(exception.object_type, 'InstanceReconcile')
        self.mox.VerifyAll()

    def test_verify_with_reconciled_data_reconcile_not_found(self):
        exists = self.mox.CreateMockAnything()
        exists.instance = INSTANCE_ID_1
        launched_at = decimal.Decimal('1.1')
        deleted_at = decimal.Decimal('2.1')
        exists.launched_at = launched_at
        exists.deleted_at = deleted_at
        results = self.mox.CreateMockAnything()
        models.InstanceReconcile.objects.filter(instance=INSTANCE_ID_1)\
                                        .AndReturn(results)
        results.count().AndReturn(1)
        launched_at = dt.dt_from_decimal(decimal.Decimal('1.1'))
        recs = self.mox.CreateMockAnything()
        models.InstanceReconcile.find(INSTANCE_ID_1, launched_at).AndReturn(recs)
        recs.count().AndReturn(0)
        self.mox.ReplayAll()
        with self.assertRaises(NotFound) as cm:
            nova_verifier._verify_with_reconciled_data(exists)
        exception = cm.exception
        self.assertEquals(exception.object_type, 'InstanceReconcile')
        self.mox.VerifyAll()


class NovaVerifierVerifyTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(models, 'InstanceExists',
                                 use_mock_anything=True)
        models.RawData.objects = self.mox.CreateMockAnything()
        self._setup_verifier()

    def _setup_verifier(self):
        self.pool = self.mox.CreateMockAnything()
        self.reconciler = self.mox.CreateMockAnything()
        config = make_verifier_config(False)
        self.verifier = nova_verifier.NovaVerifier(config,
            pool=self.pool, reconciler=self.reconciler)

    def _create_mock_logger(self):
        mock_logger = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(stacklog, 'get_logger')
        return mock_logger

    def tearDown(self):
        self.mox.UnsetStubs()
        self.verifier = None
        self.pool = None
        self.verifier_notif = None

    def test_verify_pass(self):
        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(nova_verifier, '_verify_validity')
        self.mox.StubOutWithMock(exist, 'mark_verified')
        nova_verifier._verify_for_launch(exist)
        nova_verifier._verify_for_delete(exist)
        nova_verifier._verify_validity(exist, 'all')
        exist.mark_verified()
        self.mox.ReplayAll()
        result, exists = nova_verifier._verify(exist, 'all')
        self.assertTrue(result)
        self.mox.VerifyAll()

    def test_verify_no_launched_at(self):
        exist = self.mox.CreateMockAnything()
        exist.launched_at = None
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(exist, 'mark_failed')
        exist.mark_failed(reason="Exists without a launched_at")
        self.mox.StubOutWithMock(nova_verifier, '_verify_with_reconciled_data')
        nova_verifier._verify_with_reconciled_data(exist)\
                  .AndRaise(NotFound('InstanceReconcile', {}))
        self.mox.ReplayAll()
        result, exists = nova_verifier._verify(exist, 'all')
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_verify_fails_reconciled_verify_uses_second_exception(self):
        exist = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        ex1 = VerificationException('test1')
        nova_verifier._verify_for_launch(exist).AndRaise(ex1)
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(exist, 'mark_failed')
        self.mox.StubOutWithMock(nova_verifier, '_verify_with_reconciled_data')
        nova_verifier._verify_with_reconciled_data(exist)\
                  .AndRaise(VerificationException('test2'))
        exist.mark_failed(reason='test2')
        self.mox.ReplayAll()
        result, exists = nova_verifier._verify(exist, 'none')
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_verify_launch_fail(self):
        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(exist, 'mark_failed')
        verify_exception = VerificationException('test')
        nova_verifier._verify_for_launch(exist).AndRaise(verify_exception)
        self.mox.StubOutWithMock(nova_verifier, '_verify_with_reconciled_data')
        nova_verifier._verify_with_reconciled_data(exist)\
                  .AndRaise(NotFound('InstanceReconcile', {}))
        exist.mark_failed(reason='test')
        self.mox.ReplayAll()
        result, exists = nova_verifier._verify(exist, 'none')
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_verify_fail_reconcile_success(self):
        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(exist, 'mark_verified')
        verify_exception = VerificationException('test')
        nova_verifier._verify_for_launch(exist).AndRaise(verify_exception)
        self.mox.StubOutWithMock(nova_verifier, '_verify_with_reconciled_data')
        nova_verifier._verify_with_reconciled_data(exist)
        exist.mark_verified(reconciled=True)
        self.mox.ReplayAll()
        result, exists = nova_verifier._verify(exist, 'none')
        self.assertTrue(result)
        self.mox.VerifyAll()

    def test_verify_fail_with_reconciled_data_exception(self):
        mock_logger = self._create_mock_logger()
        stacklog.get_logger('verifier', is_parent=False).AndReturn(mock_logger)
        mock_logger.exception("nova: message")

        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(exist, 'mark_failed')
        verify_exception = VerificationException('test')
        nova_verifier._verify_for_launch(exist).AndRaise(verify_exception)
        self.mox.StubOutWithMock(nova_verifier, '_verify_with_reconciled_data')
        nova_verifier._verify_with_reconciled_data(exist)\
                  .AndRaise(Exception("message"))
        exist.mark_failed(reason='Exception')
        self.mox.ReplayAll()
        result, exists = nova_verifier._verify(exist, 'none')
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_verify_delete_fail(self):
        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(exist, 'mark_failed')
        verify_exception = VerificationException('test')
        nova_verifier._verify_for_launch(exist)
        nova_verifier._verify_for_delete(exist).AndRaise(verify_exception)
        self.mox.StubOutWithMock(nova_verifier, '_verify_with_reconciled_data')
        nova_verifier._verify_with_reconciled_data(exist)\
                  .AndRaise(NotFound('InstanceReconcile', {}))
        exist.mark_failed(reason='test')
        self.mox.ReplayAll()
        result, exists = nova_verifier._verify(exist, 'none')
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_verify_exception_during_launch(self):
        mock_logger = self._create_mock_logger()
        stacklog.get_logger('verifier', is_parent=False).AndReturn(mock_logger)
        mock_logger.exception("nova: message")

        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(exist, 'mark_failed')
        nova_verifier._verify_for_launch(exist).AndRaise(Exception("message"))
        exist.mark_failed(reason='Exception')
        self.mox.ReplayAll()
        result, exists = nova_verifier._verify(exist, 'none')
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_verify_exception_during_delete(self):
        mock_logger = self._create_mock_logger()
        stacklog.get_logger('verifier', is_parent=False).AndReturn(mock_logger)
        mock_logger.exception("nova: message")

        exist = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_launch')
        self.mox.StubOutWithMock(nova_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(exist, 'mark_failed')
        nova_verifier._verify_for_launch(exist)
        nova_verifier._verify_for_delete(exist).AndRaise(Exception("message"))
        exist.mark_failed(reason='Exception')
        self.mox.ReplayAll()
        result, exists = nova_verifier._verify(exist, 'none')
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_verify_for_range_without_callback(self):
        mock_logger = self._create_mock_logger()
        stacklog.get_logger('verifier', is_parent=False).AndReturn(mock_logger)
        stacklog.get_logger('verifier', is_parent=False).AndReturn(mock_logger)
        mock_logger.info('nova: Adding 0 exists to queue.')
        mock_logger.info('nova: Adding 2 exists to queue.')
        when_max = datetime.datetime.utcnow()
        results = self.mox.CreateMockAnything()
        sent_results = self.mox.CreateMockAnything()
        models.InstanceExists.PENDING = 'pending'
        models.InstanceExists.VERIFYING = 'verifying'
        models.InstanceExists.SENT_UNVERIFIED = 'sent_unverified'
        models.InstanceExists.find(
            ending_max=when_max, status='sent_unverified').AndReturn(sent_results)
        models.InstanceExists.find(
            ending_max=when_max, status='pending').AndReturn(results)
        sent_results.count().AndReturn(0)
        results.count().AndReturn(2)
        exist1 = self.mox.CreateMockAnything()
        exist2 = self.mox.CreateMockAnything()
        results.__getslice__(0, 1000).AndReturn(results)
        results.__iter__().AndReturn([exist1, exist2].__iter__())
        exist1.update_status('verifying')
        exist2.update_status('verifying')
        exist1.save()
        exist2.save()
        self.pool.apply_async(nova_verifier._verify, args=(exist1, 'all'),
                              callback=None)
        self.pool.apply_async(nova_verifier._verify, args=(exist2, 'all'),
                              callback=None)
        self.mox.ReplayAll()
        self.verifier.verify_for_range(when_max)
        self.mox.VerifyAll()


    def test_verify_for_range_with_callback(self):
        callback = self.mox.CreateMockAnything()
        mock_logger = self._create_mock_logger()
        stacklog.get_logger('verifier', is_parent=False).AndReturn(mock_logger)
        stacklog.get_logger('verifier', is_parent=False).AndReturn(mock_logger)
        mock_logger.info('nova: Adding 0 exists to queue.')
        mock_logger.info('nova: Adding 2 exists to queue.')
        when_max = datetime.datetime.utcnow()
        results = self.mox.CreateMockAnything()
        sent_results = self.mox.CreateMockAnything()
        models.InstanceExists.PENDING = 'pending'
        models.InstanceExists.VERIFYING = 'verifying'
        models.InstanceExists.SENT_UNVERIFIED = 'sent_unverified'
        models.InstanceExists.find(
            ending_max=when_max, status='sent_unverified').AndReturn(sent_results)
        models.InstanceExists.find(
            ending_max=when_max, status='pending').AndReturn(results)
        sent_results.count().AndReturn(0)
        results.count().AndReturn(2)
        exist1 = self.mox.CreateMockAnything()
        exist2 = self.mox.CreateMockAnything()
        results.__getslice__(0, 1000).AndReturn(results)
        results.__iter__().AndReturn([exist1, exist2].__iter__())
        exist1.update_status('verifying')
        exist2.update_status('verifying')
        exist1.save()
        exist2.save()
        self.pool.apply_async(nova_verifier._verify, args=(exist1, 'all'),
                              callback=callback)
        self.pool.apply_async(nova_verifier._verify, args=(exist2, 'all'),
                              callback=callback)
        self.mox.ReplayAll()
        self.verifier.verify_for_range(when_max, callback=callback)
        self.mox.VerifyAll()


    def test_verify_for_range_when_found_sent_unverified_messages(self):
        callback = self.mox.CreateMockAnything()
        when_max = datetime.datetime.utcnow()
        results = self.mox.CreateMockAnything()
        sent_results = self.mox.CreateMockAnything()
        models.InstanceExists.PENDING = 'pending'
        models.InstanceExists.VERIFYING = 'verifying'
        models.InstanceExists.SENT_VERIFYING = 'sent_verifying'
        models.InstanceExists.SENT_UNVERIFIED = 'sent_unverified'
        models.InstanceExists.find(
            ending_max=when_max, status='sent_unverified').AndReturn(sent_results)
        models.InstanceExists.find(
            ending_max=when_max, status='pending').AndReturn(results)
        sent_results.count().AndReturn(2)
        results.count().AndReturn(0)
        exist1 = self.mox.CreateMockAnything()
        exist2 = self.mox.CreateMockAnything()
        sent_results.__getslice__(0, 1000).AndReturn(sent_results)
        sent_results.__iter__().AndReturn([exist1, exist2].__iter__())
        exist1.update_status('sent_verifying')
        exist2.update_status('sent_verifying')
        exist1.save()
        exist2.save()
        self.pool.apply_async(nova_verifier._verify, args=(exist1, 'all'),
                              callback=None)
        self.pool.apply_async(nova_verifier._verify, args=(exist2, 'all'),
                              callback=None)
        self.mox.ReplayAll()
        self.verifier.verify_for_range(when_max, callback=callback)
        self.mox.VerifyAll()

class NovaVerifierSendVerifiedNotificationTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self._setup_verifier()

    def _setup_verifier(self):
        self.pool = self.mox.CreateMockAnything()
        self.reconciler = self.mox.CreateMockAnything()
        config = make_verifier_config(False)
        self.verifier = nova_verifier.NovaVerifier(config,
            pool=self.pool, reconciler=self.reconciler)
        self.mox.StubOutWithMock(models, 'InstanceExists',
                                 use_mock_anything=True)
        models.InstanceExists.objects = self.mox.CreateMockAnything()

    def tearDown(self):
        self.mox.UnsetStubs()
        self.verifier = None
        self.pool = None
        self.verifier_notif = None

    def test_send_verified_notification_routing_keys(self):
        connection = self.mox.CreateMockAnything()
        exchange = self.mox.CreateMockAnything()
        exist = self.mox.CreateMockAnything()
        exist.id = 1
        exist.raw = self.mox.CreateMockAnything()
        exist_dict = [
            'monitor.info',
            {
                'event_type': 'test',
                'message_id': 'some_uuid'
            }
        ]
        exist_str = json.dumps(exist_dict)
        exist.raw.json = exist_str
        self.mox.StubOutWithMock(uuid, 'uuid4')
        uuid.uuid4().AndReturn('some_other_uuid')
        self.mox.StubOutWithMock(kombu.pools, 'producers')
        self.mox.StubOutWithMock(kombu.common, 'maybe_declare')
        models.InstanceExists.objects.get(id=exist.id).AndReturn(exist)
        routing_keys = ['notifications.info', 'monitor.info']
        for key in routing_keys:
            producer = self.mox.CreateMockAnything()
            producer.channel = self.mox.CreateMockAnything()
            kombu.pools.producers[connection].AndReturn(producer)
            producer.acquire(block=True).AndReturn(producer)
            producer.__enter__().AndReturn(producer)
            kombu.common.maybe_declare(exchange, producer.channel)
            message = {'event_type': NOVA_VERIFIER_EVENT_TYPE,
                       'message_id': 'some_other_uuid',
                       'original_message_id': 'some_uuid'}
            producer.publish(message, key)
            producer.__exit__(None, None, None)
        self.mox.ReplayAll()

        self.verifier.send_verified_notification(exist, exchange, connection,
                                              routing_keys=routing_keys)
        self.mox.VerifyAll()

    def test_send_verified_notification_default_routing_key(self):
        connection = self.mox.CreateMockAnything()
        exchange = self.mox.CreateMockAnything()
        exist = self.mox.CreateMockAnything()
        exist.id = 1
        exist.raw = self.mox.CreateMockAnything()
        exist_dict = [
            'monitor.info',
            {
                'event_type': 'test',
                'message_id': 'some_uuid'
            }
        ]
        exist_str = json.dumps(exist_dict)
        exist.raw.json = exist_str
        self.mox.StubOutWithMock(kombu.pools, 'producers')
        self.mox.StubOutWithMock(kombu.common, 'maybe_declare')
        models.InstanceExists.objects.get(id=exist.id).AndReturn(exist)
        producer = self.mox.CreateMockAnything()
        producer.channel = self.mox.CreateMockAnything()
        kombu.pools.producers[connection].AndReturn(producer)
        producer.acquire(block=True).AndReturn(producer)
        producer.__enter__().AndReturn(producer)
        kombu.common.maybe_declare(exchange, producer.channel)
        self.mox.StubOutWithMock(uuid, 'uuid4')
        uuid.uuid4().AndReturn('some_other_uuid')
        message = {'event_type': NOVA_VERIFIER_EVENT_TYPE,
                   'message_id': 'some_other_uuid',
                   'original_message_id': 'some_uuid'}
        producer.publish(message, exist_dict[0])
        producer.__exit__(None, None, None)
        self.mox.ReplayAll()

        self.verifier.send_verified_notification(exist, exchange, connection)
        self.mox.VerifyAll()


class NovaVerifierValidityTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self._setup_verifier()

    def _setup_verifier(self):
        self.pool = self.mox.CreateMockAnything()
        self.reconciler = self.mox.CreateMockAnything()
        config = make_verifier_config(False)
        self.verifier = nova_verifier.NovaVerifier(config,
            pool=self.pool, reconciler=self.reconciler)

    def tearDown(self):
        self.mox.UnsetStubs()

    def _create_mock_exist(self):
        exist = self.mox.CreateMockAnything()
        exist.instance = '58fb036d-5ef8-47a8-b503-7571276c400a'
        exist.tenant = '3762854cd6f6435998188d5120e4c271'
        exist.id = 23
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = decimal.Decimal('5.1')
        exist.dummy_flavor_field_name = 'dummy_flavor'
        exist.rax_options = '1'
        exist.os_architecture = 'x64'
        exist.os_distro = 'com.microsoft.server'
        exist.os_version = '2008.2'

        return exist

    def test_should_verify_that_tenant_in_exist_is_not_null(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.tenant = None
        self.mox.ReplayAll()

        with self.assertRaises(NullFieldException) as nf:
            nova_verifier._verify_validity(exist, 'all')
        exception = nf.exception
        self.assertEqual(exception.field_name, 'tenant')
        self.assertEqual(
            exception.reason, "Failed at 2014-01-02 03:04:05 UTC for "
            "58fb036d-5ef8-47a8-b503-7571276c400a: tenant field was null for "
            "exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_that_launched_at_in_exist_is_not_null(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.launched_at = None
        self.mox.ReplayAll()

        with self.assertRaises(NullFieldException) as nf:
            nova_verifier._verify_validity(exist, 'all')
        exception = nf.exception
        self.assertEqual(exception.field_name, 'launched_at')
        self.assertEqual(
            exception.reason, "Failed at 2014-01-02 03:04:05 UTC for "
            "58fb036d-5ef8-47a8-b503-7571276c400a: launched_at field was null "
            "for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_that_instance_flavor_id_in_exist_is_not_null(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.dummy_flavor_field_name = None
        self.mox.ReplayAll()

        with self.assertRaises(NullFieldException) as nf:
            nova_verifier._verify_validity(exist, 'all')
        exception = nf.exception
        self.assertEqual(exception.field_name, 'dummy_flavor_field_name')
        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for "
            "58fb036d-5ef8-47a8-b503-7571276c400a: dummy_flavor_field_name "
            "field was null for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_tenant_id_is_of_type_hex(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.tenant = 'invalid_tenant'
        self.mox.ReplayAll()

        with self.assertRaises(WrongTypeException) as wt:
            nova_verifier._verify_validity(exist, 'all')
        exception = wt.exception
        self.assertEqual(exception.field_name, 'tenant')
        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for "
            "58fb036d-5ef8-47a8-b503-7571276c400a: {tenant: invalid_tenant} "
            "was of incorrect type for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_launched_at_is_of_type_decimal(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.launched_at = 111

        self.mox.ReplayAll()

        with self.assertRaises(WrongTypeException) as wt:
            nova_verifier._verify_validity(exist, 'all')
        exception = wt.exception
        self.assertEqual(exception.field_name, 'launched_at')
        self.assertEqual(
            exception.reason,
            'Failed at 2014-01-02 03:04:05 UTC for '
            '58fb036d-5ef8-47a8-b503-7571276c400a: {launched_at: 111} was of '
            'incorrect type for exist id 23')
        self.mox.VerifyAll()

    def test_should_verify_deleted_at_is_of_decimal_type_if_present(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.deleted_at = 20
        self.mox.ReplayAll()

        with self.assertRaises(WrongTypeException) as wt:
            nova_verifier._verify_validity(exist, 'all')
        exception = wt.exception
        self.assertEqual(exception.field_name, 'deleted_at')
        self.assertEqual(
            exception.reason,
            'Failed at 2014-01-02 03:04:05 UTC for '
            '58fb036d-5ef8-47a8-b503-7571276c400a: {deleted_at: 20} was of '
            'incorrect type for exist id 23')
        self.mox.VerifyAll()

    def test_should_verify_rax_options_should_be_of_integer_type(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.rax_options = 'a'
        self.mox.ReplayAll()

        with self.assertRaises(WrongTypeException) as wt:
            nova_verifier._verify_validity(exist, 'all')
        exception = wt.exception
        self.assertEqual(exception.field_name, 'rax_options')
        self.assertEqual(
            exception.reason,
            'Failed at 2014-01-02 03:04:05 UTC for '
            '58fb036d-5ef8-47a8-b503-7571276c400a: {rax_options: a} was of '
            'incorrect type for exist id 23')
        self.mox.VerifyAll()

    def test_should_verify_rax_options_should_not_be_empty(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.rax_options = ''
        self.mox.ReplayAll()

        with self.assertRaises(NullFieldException) as nf:
            nova_verifier._verify_validity(exist, 'all')
        exception = nf.exception
        self.assertEqual(exception.field_name, 'rax_options')
        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for "
            "58fb036d-5ef8-47a8-b503-7571276c400a: rax_options field was null "
            "for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_os_arch_should_be_alphanumeric(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.os_architecture = 'x64,'
        self.mox.ReplayAll()

        with self.assertRaises(WrongTypeException) as wt:
            nova_verifier._verify_validity(exist, 'all')
        exception = wt.exception
        self.assertEqual(exception.field_name, 'os_architecture')
        self.assertEqual(
            exception.reason,
            'Failed at 2014-01-02 03:04:05 UTC for '
            '58fb036d-5ef8-47a8-b503-7571276c400a: {os_architecture: x64,} '
            'was of incorrect type for exist id 23')
        self.mox.VerifyAll()

    def test_should_verify_os_arch_should_not_be_empty(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.os_architecture = ''
        self.mox.ReplayAll()

        with self.assertRaises(NullFieldException) as nf:
            nova_verifier._verify_validity(exist, 'all')
        exception = nf.exception
        self.assertEqual(exception.field_name, 'os_architecture')
        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for "
            "58fb036d-5ef8-47a8-b503-7571276c400a: os_architecture field was "
            "null for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_os_distro_should_be_alphanumeric(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.os_distro = 'com.microsoft.server,'
        self.mox.ReplayAll()

        with self.assertRaises(WrongTypeException) as wt:
            nova_verifier._verify_validity(exist, 'all')
        exception = wt.exception
        self.assertEqual(exception.field_name, 'os_distro')
        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for "
            "58fb036d-5ef8-47a8-b503-7571276c400a: "
            "{os_distro: com.microsoft.server,} was of incorrect type for "
            "exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_os_distro_should_not_be_empty(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.os_distro = ''
        self.mox.ReplayAll()

        with self.assertRaises(NullFieldException) as nf:
            nova_verifier._verify_validity(exist, 'all')
        exception = nf.exception
        self.assertEqual(exception.field_name, 'os_distro')
        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for "
            "58fb036d-5ef8-47a8-b503-7571276c400a: os_distro field was null "
            "for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_os_version_should_be_alphanumeric(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.os_version = '2008.2,'
        self.mox.ReplayAll()

        with self.assertRaises(WrongTypeException) as wt:
            nova_verifier._verify_validity(exist, 'all')
        exception = wt.exception
        self.assertEqual(exception.field_name, 'os_version')
        self.assertEqual(
            exception.reason,
            'Failed at 2014-01-02 03:04:05 UTC for '
            '58fb036d-5ef8-47a8-b503-7571276c400a: {os_version: 2008.2,} was '
            'of incorrect type for exist id 23')
        self.mox.VerifyAll()

    def test_should_verify_os_version_should_not_be_empty(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.os_version = ''
        self.mox.ReplayAll()

        with self.assertRaises(NullFieldException) as nf:
            nova_verifier._verify_validity(exist, 'all')
        exception = nf.exception
        self.assertEqual(exception.field_name, 'os_version')
        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for "
            "58fb036d-5ef8-47a8-b503-7571276c400a: os_version field was null "
            "for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_all_exist_fields_when_validity_check_value_all(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        self.mox.ReplayAll()

        nova_verifier._verify_validity(exist, 'all')
        self.mox.VerifyAll()

    def test_should_verify_only_basic_fields_when_validity_check_basic(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self.mox.CreateMockAnything()
        exist.tenant = '3762854cd6f6435998188d5120e4c271'
        exist.id = 23
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = decimal.Decimal('5.1')
        exist.dummy_flavor_field_name = 'dummy_flavor'
        self.mox.ReplayAll()

        nova_verifier._verify_validity(exist, 'basic')
        self.mox.VerifyAll()

    def test_should_not_verify_any_fields_if_validity_check_value_is_none(self):
        exist = self.mox.CreateMockAnything()
        exist.id = 23
        self.mox.ReplayAll()

        nova_verifier._verify_validity(exist, 'none')
        self.mox.VerifyAll()

    def test_should_verify_exist_fields_even_if_deleted_at_is_none(self):
        self.mox.StubOutWithMock(config, 'flavor_field_name')
        config.flavor_field_name().AndReturn('dummy_flavor_field_name')

        exist = self._create_mock_exist()
        exist.deleted_at = None
        self.mox.ReplayAll()

        nova_verifier._verify_validity(exist, 'all')
        self.mox.VerifyAll()
