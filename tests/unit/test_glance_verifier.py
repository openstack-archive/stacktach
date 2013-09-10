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
from datetime import datetime

import decimal
import json
import uuid
import kombu

import mox

from stacktach import datetime_to_decimal as dt
from stacktach import models
from tests.unit import StacktachBaseTestCase
from utils import IMAGE_UUID_1
from utils import make_verifier_config
from verifier import glance_verifier
from verifier import FieldMismatch
from verifier import NotFound
from verifier import VerificationException


class GlanceVerifierTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(models, 'ImageUsage', use_mock_anything=True)
        models.ImageUsage.objects = self.mox.CreateMockAnything()
        self.pool = self.mox.CreateMockAnything()
        config = make_verifier_config(False)
        self.glance_verifier = glance_verifier.GlanceVerifier(config,
                                                              pool=self.pool)
        self.mox.StubOutWithMock(models, 'ImageDeletes',
                                 use_mock_anything=True)
        models.ImageDeletes.objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(models, 'ImageExists',
                                 use_mock_anything=True)

    def tearDown(self):
        self.mox.UnsetStubs()
        self.verifier = None

    def test_verify_usage_should_not_raise_exception_on_success(self):
        exist = self.mox.CreateMockAnything()
        exist.created_at = decimal.Decimal('1.1')
        exist.owner = 'owner'
        exist.size = 1234

        exist.usage = self.mox.CreateMockAnything()
        exist.usage.created_at = decimal.Decimal('1.1')
        exist.usage.size = 1234
        exist.usage.owner = 'owner'
        self.mox.ReplayAll()

        glance_verifier._verify_for_usage(exist)

        self.mox.VerifyAll()

    def test_verify_usage_created_at_mismatch(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = self.mox.CreateMockAnything()
        exist.created_at = decimal.Decimal('1.1')
        exist.usage.created_at = decimal.Decimal('2.1')
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as cm:
            glance_verifier._verify_for_usage(exist)

        exception = cm.exception
        self.assertEqual(exception.field_name, 'created_at')
        self.assertEqual(exception.expected, decimal.Decimal('1.1'))
        self.assertEqual(exception.actual, decimal.Decimal('2.1'))

        self.mox.VerifyAll()

    def test_verify_usage_owner_mismatch(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = self.mox.CreateMockAnything()
        exist.owner = 'owner'
        exist.usage.owner = 'not_owner'
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as cm:
            glance_verifier._verify_for_usage(exist)

        exception = cm.exception
        self.assertEqual(exception.field_name, 'owner')
        self.assertEqual(exception.expected, 'owner')
        self.assertEqual(exception.actual, 'not_owner')
        self.mox.VerifyAll()

    def test_verify_usage_size_mismatch(self):
        exist = self.mox.CreateMockAnything()
        exist.size = 1234

        exist.usage = self.mox.CreateMockAnything()
        exist.usage.size = 5678
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as cm:
            glance_verifier._verify_for_usage(exist)
        exception = cm.exception

        self.assertEqual(exception.field_name, 'size')
        self.assertEqual(exception.expected, 1234)
        self.assertEqual(exception.actual, 5678)

        self.mox.VerifyAll()

    def test_verify_usage_for_late_usage(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = None
        exist.uuid = IMAGE_UUID_1
        exist.created_at = decimal.Decimal('1.1')
        results = self.mox.CreateMockAnything()
        models.ImageUsage.objects.filter(uuid=IMAGE_UUID_1)\
                                    .AndReturn(results)
        results.count().AndReturn(1)
        usage = self.mox.CreateMockAnything()
        results.__getitem__(0).AndReturn(usage)
        usage.created_at = decimal.Decimal('1.1')
        self.mox.ReplayAll()

        glance_verifier._verify_for_usage(exist)
        self.mox.VerifyAll()

    def test_verify_usage_raises_not_found_for_no_usage(self):
        exist = self.mox.CreateMockAnything()
        exist.usage = None
        exist.uuid = IMAGE_UUID_1
        exist.created_at = decimal.Decimal('1.1')
        results = self.mox.CreateMockAnything()
        models.ImageUsage.objects.filter(uuid=IMAGE_UUID_1) \
            .AndReturn(results)
        results.count().AndReturn(0)
        self.mox.ReplayAll()

        with self.assertRaises(NotFound) as cm:
            glance_verifier._verify_for_usage(exist)
        exception = cm.exception
        self.assertEqual(exception.object_type, 'ImageUsage')
        self.assertEqual(exception.search_params, {'uuid': IMAGE_UUID_1})

        self.mox.VerifyAll()

    def test_verify_delete(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = self.mox.CreateMockAnything()
        exist.deleted_at = decimal.Decimal('5.1')
        exist.delete.deleted_at = decimal.Decimal('5.1')
        self.mox.ReplayAll()

        glance_verifier._verify_for_delete(exist)
        self.mox.VerifyAll()

    def test_verify_delete_when_late_delete(self):
        exist = self.mox.CreateMockAnything()
        exist.uuid = IMAGE_UUID_1
        exist.delete = None
        exist.deleted_at = decimal.Decimal('5.1')
        results = self.mox.CreateMockAnything()
        models.ImageDeletes.find(uuid=IMAGE_UUID_1).AndReturn(results)
        results.count().AndReturn(1)
        delete = self.mox.CreateMockAnything()
        delete.deleted_at = decimal.Decimal('5.1')
        results.__getitem__(0).AndReturn(delete)

        self.mox.ReplayAll()

        glance_verifier._verify_for_delete(exist)
        self.mox.VerifyAll()

    def test_verify_delete_when_no_delete(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = None
        exist.uuid = IMAGE_UUID_1
        exist.deleted_at = None
        audit_period_ending = decimal.Decimal('1.2')
        exist.audit_period_ending = audit_period_ending

        results = self.mox.CreateMockAnything()
        models.ImageDeletes.find(
            IMAGE_UUID_1, dt.dt_from_decimal(audit_period_ending)).AndReturn(
            results)
        results.count().AndReturn(0)

        self.mox.ReplayAll()

        glance_verifier._verify_for_delete(exist)
        self.mox.VerifyAll()

    def test_verify_delete_found_delete_when_exist_deleted_at_is_none(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = None
        exist.uuid = IMAGE_UUID_1
        audit_period_ending = decimal.Decimal('1.3')
        exist.deleted_at = None
        exist.audit_period_ending = audit_period_ending
        results = self.mox.CreateMockAnything()
        models.ImageDeletes.find(
            IMAGE_UUID_1, dt.dt_from_decimal(audit_period_ending)).AndReturn(
            results)
        results.count().AndReturn(1)

        self.mox.ReplayAll()

        with self.assertRaises(VerificationException) as ve:
            glance_verifier._verify_for_delete(exist)
        exception = ve.exception
        self.assertEqual(exception.reason,
                         'Found ImageDeletes for non-delete exist')

        self.mox.VerifyAll()

    def test_verify_delete_deleted_at_mismatch(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = self.mox.CreateMockAnything()
        exist.deleted_at = decimal.Decimal('5.1')
        exist.delete.deleted_at = decimal.Decimal('4.1')
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as fm:
            glance_verifier._verify_for_delete(exist)
        exception = fm.exception
        self.assertEqual(exception.field_name, 'deleted_at')
        self.assertEqual(exception.expected, decimal.Decimal('5.1'))
        self.assertEqual(exception.actual, decimal.Decimal('4.1'))
        self.mox.VerifyAll()

    def test_verify_for_delete_size_mismatch(self):
        exist = self.mox.CreateMockAnything()
        exist.delete = self.mox.CreateMockAnything()
        exist.launched_at = decimal.Decimal('1.1')
        exist.deleted_at = decimal.Decimal('5.1')
        exist.delete.launched_at = decimal.Decimal('1.1')
        exist.delete.deleted_at = decimal.Decimal('6.1')
        self.mox.ReplayAll()

        try:
            glance_verifier._verify_for_delete(exist)
            self.fail()
        except FieldMismatch, fm:
            self.assertEqual(fm.field_name, 'deleted_at')
            self.assertEqual(fm.expected, decimal.Decimal('5.1'))
            self.assertEqual(fm.actual, decimal.Decimal('6.1'))
        self.mox.VerifyAll()

    def test_verify_should_verify_exists_for_usage_and_delete(self):
        exist = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(glance_verifier, '_verify_for_usage')
        glance_verifier._verify_for_usage(exist)
        self.mox.StubOutWithMock(glance_verifier, '_verify_for_delete')
        glance_verifier._verify_for_delete(exist)
        exist.mark_verified()
        self.mox.ReplayAll()

        verified, exist = glance_verifier._verify(exist)

        self.mox.VerifyAll()
        self.assertTrue(verified)


    def test_verify_exist_marks_exist_as_failed_if_field_mismatch_exception_is_raised(self):
        exist = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(glance_verifier, '_verify_for_usage')
        field_mismatch_exc = FieldMismatch('field', 'expected', 'actual')
        glance_verifier._verify_for_usage(exist).AndRaise(exception=field_mismatch_exc)
        exist.mark_failed(reason='FieldMismatch')
        self.mox.ReplayAll()

        verified, exist = glance_verifier._verify(exist)

        self.mox.VerifyAll()
        self.assertFalse(verified)

    def test_verify_for_range_without_callback(self):
        when_max = datetime.utcnow()
        results = self.mox.CreateMockAnything()
        models.ImageExists.PENDING = 'pending'
        models.ImageExists.VERIFYING = 'verifying'
        self.mox.StubOutWithMock(models.ImageExists, 'find')
        models.ImageExists.find(
            ending_max=when_max,
            status=models.ImageExists.PENDING).AndReturn(results)
        results.count().AndReturn(2)
        exist1 = self.mox.CreateMockAnything()
        exist2 = self.mox.CreateMockAnything()
        results.__getslice__(0, 1000).AndReturn(results)
        results.__iter__().AndReturn([exist1, exist2].__iter__())
        exist1.save()
        exist2.save()
        self.pool.apply_async(glance_verifier._verify, args=(exist1,),
                              callback=None)
        self.pool.apply_async(glance_verifier._verify, args=(exist2,),
                              callback=None)
        self.mox.ReplayAll()

        self.glance_verifier.verify_for_range(when_max)
        self.assertEqual(exist1.status, 'verifying')
        self.assertEqual(exist2.status, 'verifying')
        self.mox.VerifyAll()

    def test_verify_for_range_with_callback(self):
        callback = self.mox.CreateMockAnything()
        when_max = datetime.utcnow()
        results = self.mox.CreateMockAnything()
        models.ImageExists.PENDING = 'pending'
        models.ImageExists.VERIFYING = 'verifying'
        models.ImageExists.find(
            ending_max=when_max,
            status=models.ImageExists.PENDING).AndReturn(results)
        results.count().AndReturn(2)
        exist1 = self.mox.CreateMockAnything()
        exist2 = self.mox.CreateMockAnything()
        results.__getslice__(0, 1000).AndReturn(results)
        results.__iter__().AndReturn([exist1, exist2].__iter__())
        exist1.save()
        exist2.save()
        self.pool.apply_async(glance_verifier._verify, args=(exist1,),
                              callback=callback)
        self.pool.apply_async(glance_verifier._verify, args=(exist2,),
                              callback=callback)
        self.mox.ReplayAll()
        self.glance_verifier.verify_for_range(
            when_max, callback=callback)
        self.assertEqual(exist1.status, 'verifying')
        self.assertEqual(exist2.status, 'verifying')
        self.mox.VerifyAll()

    def test_send_verified_notification_routing_keys(self):
        connection = self.mox.CreateMockAnything()
        exchange = self.mox.CreateMockAnything()
        exist = self.mox.CreateMockAnything()
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
        routing_keys = ['notifications.info', 'monitor.info']
        for key in routing_keys:
            producer = self.mox.CreateMockAnything()
            producer.channel = self.mox.CreateMockAnything()
            kombu.pools.producers[connection].AndReturn(producer)
            producer.acquire(block=True).AndReturn(producer)
            producer.__enter__().AndReturn(producer)
            kombu.common.maybe_declare(exchange, producer.channel)
            message = {'event_type': 'image.exists.verified.old',
                       'message_id': 'some_other_uuid',
                       'original_message_id': 'some_uuid'}
            producer.publish(message, key)
            producer.__exit__(None, None, None)
        self.mox.ReplayAll()

        self.glance_verifier.send_verified_notification(
            exist, exchange, connection, routing_keys=routing_keys)
        self.mox.VerifyAll()

    def test_send_verified_notification_default_routing_key(self):
        connection = self.mox.CreateMockAnything()
        exchange = self.mox.CreateMockAnything()
        exist = self.mox.CreateMockAnything()
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
        producer = self.mox.CreateMockAnything()
        producer.channel = self.mox.CreateMockAnything()
        kombu.pools.producers[connection].AndReturn(producer)
        producer.acquire(block=True).AndReturn(producer)
        producer.__enter__().AndReturn(producer)
        kombu.common.maybe_declare(exchange, producer.channel)
        self.mox.StubOutWithMock(uuid, 'uuid4')
        uuid.uuid4().AndReturn('some_other_uuid')
        message = {'event_type': 'image.exists.verified.old',
                   'message_id': 'some_other_uuid',
                   'original_message_id': 'some_uuid'}
        producer.publish(message, exist_dict[0])
        producer.__exit__(None, None, None)
        self.mox.ReplayAll()

        self.glance_verifier.send_verified_notification(exist, exchange,
                                                        connection)
        self.mox.VerifyAll()