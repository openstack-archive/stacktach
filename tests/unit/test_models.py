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

import unittest
import mox
from stacktach.models import RawData, GlanceRawData, GenericRawData
from stacktach.models import ImageDeletes, InstanceExists, ImageExists
from tests.unit.utils import IMAGE_UUID_1
from stacktach import datetime_to_decimal as dt
from tests.unit import StacktachBaseTestCase


class ModelsTestCase(StacktachBaseTestCase):
    def test_get_name_for_rawdata(self):
        self.assertEquals(RawData.get_name(), 'RawData')

    def test_get_name_for_glancerawdata(self):
        self.assertEquals(GlanceRawData.get_name(), 'GlanceRawData')

    def test_get_name_for_genericrawdata(self):
        self.assertEquals(GenericRawData.get_name(), 'GenericRawData')


class ImageDeletesTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_find_delete_should_return_delete_issued_before_given_time(self):
        delete = self.mox.CreateMockAnything()
        deleted_max = datetime.utcnow()
        self.mox.StubOutWithMock(ImageDeletes.objects, 'filter')
        ImageDeletes.objects.filter(
            uuid=IMAGE_UUID_1,
            deleted_at__lte=dt.dt_to_decimal(deleted_max)).AndReturn(delete)
        self.mox.ReplayAll()

        self.assertEquals(ImageDeletes.find(
            IMAGE_UUID_1, deleted_max), delete)
        self.mox.VerifyAll()

    def test_find_delete_should_return_delete_with_the_given_uuid(self):
        delete = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(ImageDeletes.objects, 'filter')
        ImageDeletes.objects.filter(uuid=IMAGE_UUID_1).AndReturn(delete)
        self.mox.ReplayAll()

        self.assertEquals(ImageDeletes.find(IMAGE_UUID_1, None), delete)
        self.mox.VerifyAll()


class ImageExistsTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_group_exists_with_date_status_in_audit_period_by_owner_rawid(self):
        end_max = datetime.utcnow()
        status = 'pending'
        exist1 = self.mox.CreateMockAnything()
        exist1.owner = "owner1"
        exist1.raw_id = "1"
        exist2 = self.mox.CreateMockAnything()
        exist2.owner = "owner2"
        exist2.raw_id = "2"
        exist3 = self.mox.CreateMockAnything()
        exist3.owner = "owner1"
        exist3.raw_id = "1"
        exist4 = self.mox.CreateMockAnything()
        exist4.owner = "owner1"
        exist4.raw_id = "3"

        ordered_results = [exist1, exist3, exist4, exist2]
        unordered_results = self.mox.CreateMockAnything()
        related_results = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(ImageExists.objects, 'select_related')
        ImageExists.objects.select_related().AndReturn(related_results)
        related_results.filter(
            audit_period_ending__lte=dt.dt_to_decimal(end_max),
            status=status).AndReturn(unordered_results)
        unordered_results.order_by('owner').AndReturn(ordered_results)
        self.mox.ReplayAll()

        results = ImageExists.find_and_group_by_owner_and_raw_id(end_max,
                                                                 status)

        self.mox.VerifyAll()
        self.assertEqual(results, {'owner1-1': [exist1, exist3],
                                   'owner1-3': [exist4],
                                   'owner2-2': [exist2]})

    def test_mark_exists_as_sent_unverified(self):
        message_ids = ["0708cb0b-6169-4d7c-9f58-3cf3d5bf694b",
                       "9156b83e-f684-4ec3-8f94-7e41902f27aa"]

        exist1 = self.mox.CreateMockAnything()
        exist1.status = "pending"
        exist1.save()
        exist2 = self.mox.CreateMockAnything()
        exist2.status = "pending"
        exist2.save()
        exist3 = self.mox.CreateMockAnything()
        exist3.status = "pending"
        exist3.save()
        self.mox.StubOutWithMock(ImageExists.objects, 'filter')
        ImageExists.objects.filter(message_id=message_ids[0]).AndReturn(
            [exist1, exist2])
        ImageExists.objects.filter(message_id=message_ids[1]).AndReturn(
            [exist3])
        self.mox.ReplayAll()

        results = ImageExists.mark_exists_as_sent_unverified(message_ids)

        self.assertEqual(results, ([], []))
        self.assertEqual(exist1.send_status, '201')
        self.assertEqual(exist2.send_status, '201')
        self.assertEqual(exist3.send_status, '201')

        self.mox.VerifyAll()

    def test_mark_exists_as_sent_unverified_return_absent_exists(self):
        message_ids = ["0708cb0b-6169-4d7c-9f58-3cf3d5bf694b",
                       "9156b83e-f684-4ec3-8f94-7e41902f27aa"]

        exist1 = self.mox.CreateMockAnything()
        exist1.status = "pending"
        exist1.save()
        exist2 = self.mox.CreateMockAnything()
        exist2.status = "pending"
        exist2.save()
        self.mox.StubOutWithMock(ImageExists.objects, 'filter')
        ImageExists.objects.filter(message_id=message_ids[0]).AndReturn(
            [exist1, exist2])
        ImageExists.objects.filter(message_id=message_ids[1]).AndReturn([])
        self.mox.ReplayAll()

        results = ImageExists.mark_exists_as_sent_unverified(message_ids)

        self.assertEqual(results, (['9156b83e-f684-4ec3-8f94-7e41902f27aa'],
                                   []))
        self.assertEqual(exist1.send_status, '201')
        self.assertEqual(exist2.send_status, '201')

        self.mox.VerifyAll()

    def test_mark_exists_as_sent_unverified_and_return_exist_not_pending(self):
        message_ids = ["0708cb0b-6169-4d7c-9f58-3cf3d5bf694b",
                       "9156b83e-f684-4ec3-8f94-7e41902f27aa"]

        exist1 = self.mox.CreateMockAnything()
        exist1.status = "pending"
        exist1.save()
        exist2 = self.mox.CreateMockAnything()
        exist2.status = "verified"
        exist3 = self.mox.CreateMockAnything()
        exist3.status = "pending"
        exist3.save()
        self.mox.StubOutWithMock(ImageExists.objects, 'filter')
        ImageExists.objects.filter(message_id=message_ids[0]).AndReturn(
            [exist1, exist2])
        ImageExists.objects.filter(message_id=message_ids[1]).AndReturn(
            [exist3])
        self.mox.ReplayAll()

        results = ImageExists.mark_exists_as_sent_unverified(message_ids)

        self.assertEqual(results, ([],
                                   ["0708cb0b-6169-4d7c-9f58-3cf3d5bf694b"]))
        self.assertEqual(exist1.send_status, '201')
        self.assertEqual(exist3.send_status, '201')
        self.mox.VerifyAll()


class InstanceExistsTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_find_should_return_records_with_date_and_status_in_audit_period(self):
        end_max = datetime.utcnow()
        status = 'pending'
        unordered_results = self.mox.CreateMockAnything()
        expected_results = [1, 2]
        related_results = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(InstanceExists.objects, 'select_related')
        InstanceExists.objects.select_related().AndReturn(related_results)
        related_results.filter(audit_period_ending__lte=dt.dt_to_decimal(
            end_max), status=status).AndReturn(unordered_results)
        unordered_results.order_by('id').AndReturn(expected_results)
        self.mox.ReplayAll()

        results = InstanceExists.find(end_max, status)

        self.mox.VerifyAll()
        self.assertEqual(results, [1, 2])

    def test_mark_exists_as_sent_unverified(self):
        message_ids = ["0708cb0b-6169-4d7c-9f58-3cf3d5bf694b",
                       "9156b83e-f684-4ec3-8f94-7e41902f27aa"]

        exist1 = self.mox.CreateMockAnything()
        exist1.status = "pending"
        exist1.save()
        exist2 = self.mox.CreateMockAnything()
        exist2.status = "pending"
        exist2.save()
        self.mox.StubOutWithMock(InstanceExists.objects, 'get')
        InstanceExists.objects.get(message_id=message_ids[0]).AndReturn(exist1)
        InstanceExists.objects.get(message_id=message_ids[1]).AndReturn(exist2)
        self.mox.ReplayAll()

        results = InstanceExists.mark_exists_as_sent_unverified(message_ids)

        self.assertEqual(results, ([], []))
        self.assertEqual(exist1.send_status, '201')
        self.assertEqual(exist2.send_status, '201')
        self.mox.VerifyAll()

    def test_mark_exists_as_sent_unverified_return_absent_exists(self):
        message_ids = ["0708cb0b-6169-4d7c-9f58-3cf3d5bf694b",
                       "9156b83e-f684-4ec3-8f94-7e41902f27aa"]

        exist1 = self.mox.CreateMockAnything()
        exist1.status = "pending"
        exist1.save()
        self.mox.StubOutWithMock(InstanceExists.objects, 'get')
        InstanceExists.objects.get(message_id=message_ids[0]).AndReturn(exist1)
        InstanceExists.objects.get(message_id=message_ids[1]).AndRaise(
            Exception)
        self.mox.ReplayAll()

        results = InstanceExists.mark_exists_as_sent_unverified(message_ids)

        self.assertEqual(results, (['9156b83e-f684-4ec3-8f94-7e41902f27aa'],
                                   []))
        self.assertEqual(exist1.send_status, '201')
        self.mox.VerifyAll()

    def test_mark_exists_as_sent_unverified_and_return_exist_not_pending(self):
        message_ids = ["0708cb0b-6169-4d7c-9f58-3cf3d5bf694b",
                       "9156b83e-f684-4ec3-8f94-7e41902f27aa"]

        exist1 = self.mox.CreateMockAnything()
        exist1.status = "pending"
        exist1.save()
        exist2 = self.mox.CreateMockAnything()
        exist2.status = "verified"
        self.mox.StubOutWithMock(InstanceExists.objects, 'get')
        InstanceExists.objects.get(message_id=message_ids[0]).AndReturn(exist1)
        InstanceExists.objects.get(message_id=message_ids[1]).AndReturn(exist2)
        self.mox.ReplayAll()

        results = InstanceExists.mark_exists_as_sent_unverified(message_ids)

        self.assertEqual(results, ([],
                                   ["9156b83e-f684-4ec3-8f94-7e41902f27aa"]))
        self.assertEqual(exist1.send_status, '201')
        self.mox.VerifyAll()

