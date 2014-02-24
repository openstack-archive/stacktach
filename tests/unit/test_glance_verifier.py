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
import kombu

import mox

from stacktach import datetime_to_decimal as dt
from stacktach import stacklog
from stacktach import models
from tests.unit import StacktachBaseTestCase
from utils import IMAGE_UUID_1, SIZE_1, SIZE_2, CREATED_AT_1, CREATED_AT_2
from utils import GLANCE_VERIFIER_EVENT_TYPE
from utils import make_verifier_config
from verifier import glance_verifier
from verifier import NullFieldException
from verifier import WrongTypeException
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
        models.ImageExists.objects = self.mox.CreateMockAnything()

    def tearDown(self):
        self.mox.UnsetStubs()
        self.verifier = None

    def _setup_mock_logger(self):
        mock_logger = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(stacklog, 'get_logger')
        stacklog.get_logger('verifier', is_parent=False).AndReturn(mock_logger)
        return mock_logger

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
        exist.created_at = CREATED_AT_1
        exist.usage.created_at = CREATED_AT_2
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as cm:
            glance_verifier._verify_for_usage(exist)

        exception = cm.exception
        self.assertEqual(exception.field_name, 'created_at')
        self.assertEqual(exception.expected, CREATED_AT_1)
        self.assertEqual(exception.actual, CREATED_AT_2)

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
        exist.size = SIZE_1

        exist.usage = self.mox.CreateMockAnything()
        exist.usage.size = SIZE_2
        self.mox.ReplayAll()

        with self.assertRaises(FieldMismatch) as cm:
            glance_verifier._verify_for_usage(exist)
        exception = cm.exception

        self.assertEqual(exception.field_name, 'size')
        self.assertEqual(exception.expected, SIZE_1)
        self.assertEqual(exception.actual, SIZE_2)

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

    def test_should_verify_that_image_size_in_exist_is_not_null(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        exist = self.mox.CreateMockAnything()
        exist.id = 23
        exist.size = None
        exist.created_at = decimal.Decimal('5.1')
        exist.uuid = '1234-5678-9012-3456'
        self.mox.ReplayAll()

        try:
            glance_verifier._verify_validity(exist)
            self.fail()
        except NullFieldException as nf:
            self.assertEqual(nf.field_name, 'image_size')
            self.assertEqual(
                nf.reason, "Failed at 2014-01-02 03:04:05 UTC for "
                "1234-5678-9012-3456: image_size field was null for "
                "exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_that_created_at_in_exist_is_not_null(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-01 01:02:03')
        self.mox.ReplayAll()

        exist = self.mox.CreateMockAnything()
        exist.id = 23
        exist.size = 'size'
        exist.created_at = None
        exist.uuid = '1234-5678-9012-3456'
        self.mox.ReplayAll()

        with self.assertRaises(NullFieldException) as nfe:
            glance_verifier._verify_validity(exist)
        exception = nfe.exception

        self.assertEqual(exception.field_name, 'created_at')
        self.assertEqual(exception.reason,
                         "Failed at 2014-01-01 01:02:03 UTC for "
                         "1234-5678-9012-3456: created_at field was "
                         "null for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_that_uuid_in_exist_is_not_null(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-01 01:02:03')
        self.mox.ReplayAll()

        exist = self.mox.CreateMockAnything()
        exist.id = 23
        exist.size = 'size'
        exist.created_at = decimal.Decimal('5.1')
        exist.uuid = None
        self.mox.ReplayAll()

        try:
            glance_verifier._verify_validity(exist)
            self.fail()
        except NullFieldException as nf:
            self.assertEqual(nf.field_name, 'uuid')
            self.assertEqual(
                nf.reason, "Failed at 2014-01-01 01:02:03 UTC for None: "
                           "uuid field was null for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_that_owner_in_exist_is_not_null(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        exist = self.mox.CreateMockAnything()
        exist.id = 23
        exist.size = 1234
        exist.created_at = decimal.Decimal('5.1')
        exist.uuid = '1234-5678-9012-3456'
        exist.owner = None
        self.mox.ReplayAll()

        try:
            glance_verifier._verify_validity(exist)
            self.fail()
        except NullFieldException as nf:
            self.assertEqual(nf.field_name, 'owner')
            self.assertEqual(
                nf.reason, "Failed at 2014-01-02 03:04:05 UTC for "
                "1234-5678-9012-3456: owner field was null for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_that_uuid_value_is_uuid_like(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        exist = self.mox.CreateMockAnything()
        exist.id = 23
        exist.size = 'size'
        exist.created_at = decimal.Decimal('5.1')
        exist.uuid = "asdfe-fgh"
        self.mox.ReplayAll()

        try:
            glance_verifier._verify_validity(exist)
            self.fail()
        except WrongTypeException as wt:
            self.assertEqual(wt.field_name, 'uuid')
            self.assertEqual(
                wt.reason,
                "Failed at 2014-01-02 03:04:05 UTC for None: "
                "{uuid: asdfe-fgh} was of incorrect type for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_created_at_is_decimal(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        exist = self.mox.CreateMockAnything()
        exist.id = 23
        exist.size = 'size'
        exist.created_at = "123.a"
        exist.uuid = "58fb036d-5ef8-47a8-b503-7571276c400a"
        self.mox.ReplayAll()

        try:
            glance_verifier._verify_validity(exist)
            self.fail()
        except WrongTypeException as wt:
            self.assertEqual(wt.field_name, 'created_at')
            self.assertEqual(
                wt.reason,
                "Failed at 2014-01-02 03:04:05 UTC for "
                "58fb036d-5ef8-47a8-b503-7571276c400a: {created_at: 123.a} was "
                "of incorrect type for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_image_size_is_of_type_decimal(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        exist = self.mox.CreateMockAnything()
        exist.id = 23
        exist.size = 'random'
        exist.created_at = decimal.Decimal('5.1')
        exist.uuid = "58fb036d-5ef8-47a8-b503-7571276c400a"
        self.mox.ReplayAll()

        try:
            glance_verifier._verify_validity(exist)
            self.fail()
        except WrongTypeException as wt:
            self.assertEqual(wt.field_name, 'size')
            self.assertEqual(
                wt.reason,
                "Failed at 2014-01-02 03:04:05 UTC for "
                "58fb036d-5ef8-47a8-b503-7571276c400a: {size: random} was "
                "of incorrect type for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_owner_is_of_type_hex(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        exist = self.mox.CreateMockAnything()
        exist.id = 23
        exist.size = 1234L
        exist.created_at = decimal.Decimal('5.1')
        exist.uuid = "58fb036d-5ef8-47a8-b503-7571276c400a"
        exist.owner = "3762854cd6f6435998188d5120e4c271,kl"
        self.mox.ReplayAll()

        try:
            glance_verifier._verify_validity(exist)
            self.fail()
        except WrongTypeException as wt:
            self.assertEqual(wt.field_name, 'owner')
            self.assertEqual(
                wt.reason,
                "Failed at 2014-01-02 03:04:05 UTC for "
                "58fb036d-5ef8-47a8-b503-7571276c400a: "
                "{owner: 3762854cd6f6435998188d5120e4c271,kl} was of "
                "incorrect type for exist id 23")
        self.mox.VerifyAll()

    def test_should_verify_correctly_for_all_non_null_and_valid_types(self):
        exist = self.mox.CreateMockAnything()
        exist.id = 23
        exist.size = 983040L
        exist.created_at = decimal.Decimal('5.1')
        exist.uuid = "58fb036d-5ef8-47a8-b503-7571276c400a"
        exist.owner = "3762854cd6f6435998188d5120e4c271"
        self.mox.ReplayAll()

        glance_verifier._verify_validity(exist)
        self.mox.VerifyAll()

    def test_verify_should_verify_exists_for_usage_and_delete(self):
        exist1 = self.mox.CreateMockAnything()
        exist2 = self.mox.CreateMockAnything()

        self.mox.StubOutWithMock(glance_verifier, '_verify_for_usage')
        self.mox.StubOutWithMock(glance_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(glance_verifier, '_verify_validity')
        for exist in [exist1, exist2]:
            glance_verifier._verify_for_usage(exist)
            glance_verifier._verify_for_delete(exist)
            glance_verifier._verify_validity(exist)
            exist.mark_verified()
        self.mox.ReplayAll()

        verified, exist = glance_verifier._verify([exist1, exist2])

        self.mox.VerifyAll()
        self.assertTrue(verified)

    def test_verify_exist_marks_exist_failed_if_field_mismatch_exception(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-01 01:01:01')
        self.mox.ReplayAll()

        exist1 = self.mox.CreateMockAnything()
        exist2 = self.mox.CreateMockAnything()

        self.mox.StubOutWithMock(glance_verifier, '_verify_for_usage')
        self.mox.StubOutWithMock(glance_verifier, '_verify_for_delete')
        self.mox.StubOutWithMock(glance_verifier, '_verify_validity')
        field_mismatch_exc = FieldMismatch('field', 'expected',
                                           'actual', 'uuid')
        glance_verifier._verify_for_usage(exist1).AndRaise(
            exception=field_mismatch_exc)
        exist1.mark_failed(
            reason="Failed at 2014-01-01 01:01:01 UTC for uuid: Expected "
                   "field to be 'expected' got 'actual'")

        glance_verifier._verify_for_usage(exist2)
        glance_verifier._verify_for_delete(exist2)
        glance_verifier._verify_validity(exist2)
        exist2.mark_verified()
        self.mox.ReplayAll()

        verified, exist = glance_verifier._verify([exist1, exist2])
        self.mox.VerifyAll()
        self.assertFalse(verified)


    def test_verify_for_range_without_callback_for_sent_unverified(self):
        mock_logger = self._setup_mock_logger()
        self.mox.StubOutWithMock(mock_logger, 'info')
        stacklog.get_logger('verifier', is_parent=False).AndReturn(mock_logger)
        mock_logger.info('glance: Adding 2 per-owner exists to queue.')
        mock_logger.info('glance: Adding 2 per-owner exists to queue.')
        when_max = datetime.datetime.utcnow()
        models.ImageExists.VERIFYING = 'verifying'
        models.ImageExists.PENDING = 'pending'
        models.ImageExists.SENT_VERIFYING = 'sent_verifying'
        models.ImageExists.SENT_UNVERIFIED = 'sent_unverified'
        self.mox.StubOutWithMock(models.ImageExists, 'find')
        exist1 = self.mox.CreateMockAnything()
        exist2 = self.mox.CreateMockAnything()
        exist3 = self.mox.CreateMockAnything()
        exist4 = self.mox.CreateMockAnything()
        exist5 = self.mox.CreateMockAnything()
        results = {'owner1': [exist1, exist2], 'owner2': [exist3]}
        sent_results = {'owner1': [exist4], 'owner2': [exist5]}
        models.ImageExists.find_and_group_by_owner_and_raw_id(
            ending_max=when_max,
            status=models.ImageExists.SENT_UNVERIFIED).AndReturn(sent_results)
        models.ImageExists.find_and_group_by_owner_and_raw_id(
            ending_max=when_max,
            status=models.ImageExists.PENDING).AndReturn(results)
        exist1.save()
        exist2.save()
        exist3.save()
        exist4.save()
        exist5.save()
        self.pool.apply_async(glance_verifier._verify,
                              args=([exist4],), callback=None)
        self.pool.apply_async(glance_verifier._verify, args=([exist5],),
                              callback=None)
        self.pool.apply_async(glance_verifier._verify,
                              args=([exist1, exist2],), callback=None)
        self.pool.apply_async(glance_verifier._verify, args=([exist3],),
                              callback=None)
        self.mox.ReplayAll()

        self.glance_verifier.verify_for_range(when_max)
        self.assertEqual(exist1.status, 'verifying')
        self.assertEqual(exist2.status, 'verifying')
        self.assertEqual(exist3.status, 'verifying')
        self.assertEqual(exist4.status, 'sent_verifying')
        self.assertEqual(exist5.status, 'sent_verifying')
        self.mox.VerifyAll()

    def test_verify_for_range_with_callback(self):
        mock_logger = self._setup_mock_logger()
        self.mox.StubOutWithMock(mock_logger, 'info')
        stacklog.get_logger('verifier', is_parent=False).AndReturn(mock_logger)
        mock_logger.info('glance: Adding 0 per-owner exists to queue.')
        mock_logger.info('glance: Adding 2 per-owner exists to queue.')
        callback = self.mox.CreateMockAnything()
        when_max = datetime.datetime.utcnow()
        models.ImageExists.SENT_VERIFYING = 'sent_verifying'
        models.ImageExists.SENT_UNVERIFIED = 'sent_unverified'
        models.ImageExists.PENDING = 'pending'
        models.ImageExists.VERIFYING = 'verifying'
        exist1 = self.mox.CreateMockAnything()
        exist2 = self.mox.CreateMockAnything()
        exist3 = self.mox.CreateMockAnything()
        results = {'owner1': [exist1, exist2], 'owner2': [exist3]}
        models.ImageExists.find_and_group_by_owner_and_raw_id(
            ending_max=when_max,
            status=models.ImageExists.SENT_UNVERIFIED).AndReturn([])
        models.ImageExists.find_and_group_by_owner_and_raw_id(
            ending_max=when_max,
            status=models.ImageExists.PENDING).AndReturn(results)
        exist1.save()
        exist2.save()
        exist3.save()
        self.pool.apply_async(glance_verifier._verify, args=([exist1, exist2],),
                              callback=callback)
        self.pool.apply_async(glance_verifier._verify, args=([exist3],),
                              callback=callback)
        self.mox.ReplayAll()
        self.glance_verifier.verify_for_range(
            when_max, callback=callback)
        self.assertEqual(exist1.status, 'verifying')
        self.assertEqual(exist2.status, 'verifying')
        self.assertEqual(exist3.status, 'verifying')
        self.mox.VerifyAll()

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
        exist.audit_period_beginning = datetime.datetime(2013, 10, 10)
        exist.audit_period_ending = datetime.datetime(2013, 10, 10, 23, 59, 59)
        exist.owner = "1"
        self.mox.StubOutWithMock(uuid, 'uuid4')
        uuid.uuid4().AndReturn('some_other_uuid')
        self.mox.StubOutWithMock(kombu.pools, 'producers')
        self.mox.StubOutWithMock(kombu.common, 'maybe_declare')
        models.ImageExists.objects.get(id=exist.id).AndReturn(exist)
        routing_keys = ['notifications.info', 'monitor.info']
        for key in routing_keys:
            producer = self.mox.CreateMockAnything()
            producer.channel = self.mox.CreateMockAnything()
            kombu.pools.producers[connection].AndReturn(producer)
            producer.acquire(block=True).AndReturn(producer)
            producer.__enter__().AndReturn(producer)
            kombu.common.maybe_declare(exchange, producer.channel)
            message = {'event_type': GLANCE_VERIFIER_EVENT_TYPE,
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
        exist.audit_period_beginning = datetime.datetime(2013, 10, 10)
        exist.audit_period_ending = datetime.datetime(2013, 10, 10, 23, 59, 59)
        exist.owner = "1"
        self.mox.StubOutWithMock(kombu.pools, 'producers')
        self.mox.StubOutWithMock(kombu.common, 'maybe_declare')
        models.ImageExists.objects.get(id=exist.id).AndReturn(exist)
        producer = self.mox.CreateMockAnything()
        producer.channel = self.mox.CreateMockAnything()
        kombu.pools.producers[connection].AndReturn(producer)
        producer.acquire(block=True).AndReturn(producer)
        producer.__enter__().AndReturn(producer)
        kombu.common.maybe_declare(exchange, producer.channel)
        self.mox.StubOutWithMock(uuid, 'uuid4')
        uuid.uuid4().AndReturn('some_other_uuid')
        message = {'event_type': GLANCE_VERIFIER_EVENT_TYPE,
                   'message_id': 'some_other_uuid',
                   'original_message_id': 'some_uuid'}
        producer.publish(message, exist_dict[0])
        producer.__exit__(None, None, None)
        self.mox.ReplayAll()

        self.glance_verifier.send_verified_notification(exist, exchange,
                                                        connection)
        self.mox.VerifyAll()
