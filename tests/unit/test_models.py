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
from django.db.models import Q
import mox
from stacktach.models import RawData, GlanceRawData, GenericRawData, ImageDeletes, InstanceExists, ImageExists
from tests.unit.utils import IMAGE_UUID_1
from stacktach import datetime_to_decimal as dt, models
from stacktach.models import RawData, GlanceRawData, GenericRawData
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

    def test_find_should_return_records_with_date_and_status_in_audit_period(self):
        end_max = datetime.utcnow()
        status = 'pending'
        unordered_results = self.mox.CreateMockAnything()
        expected_results = [1, 2]
        related_results = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(ImageExists.objects, 'select_related')
        ImageExists.objects.select_related().AndReturn(related_results)
        related_results.filter(audit_period_ending__lte=dt.dt_to_decimal(
            end_max), status=status).AndReturn(unordered_results)
        unordered_results.order_by('id').AndReturn(expected_results)
        self.mox.ReplayAll()

        results = ImageExists.find(end_max, status)

        self.mox.VerifyAll()
        self.assertEqual(results, [1, 2])

    def test_return_true_if_all_exists_for_owner_are_verified(self):
        owner = "1"
        audit_period_beginning = datetime(2013, 10, 10)
        audit_period_ending = datetime(2013, 10, 10, 23, 59, 59)

        results = self.mox.CreateMockAnything()
        results.count().AndReturn(0)

        self.mox.StubOutWithMock(ImageExists.objects, 'filter')
        ImageExists.objects.filter(
            mox.IgnoreArg(), owner=owner,
            audit_period_beginning=audit_period_beginning,
            audit_period_ending=audit_period_ending).AndReturn(results)
        self.mox.ReplayAll()

        self.assertTrue(models.ImageExists.are_all_exists_for_owner_verified(
            owner, audit_period_beginning, audit_period_ending))
        self.mox.VerifyAll()

    def test_return_false_if_all_exists_for_owner_are_verified(self):
        owner = "1"
        audit_period_beginning = datetime(2013, 10, 10)
        audit_period_ending = datetime(2013, 10, 10, 23, 59, 59)
        results = self.mox.CreateMockAnything()
        results.count().AndReturn(1)

        self.mox.StubOutWithMock(ImageExists.objects, 'filter')
        ImageExists.objects.filter(
            mox.IgnoreArg(), owner=owner,
            audit_period_beginning=audit_period_beginning,
            audit_period_ending=audit_period_ending).AndReturn(results)
        self.mox.ReplayAll()

        self.assertFalse(ImageExists.are_all_exists_for_owner_verified(
            owner=owner, audit_period_beginning=audit_period_beginning,
            audit_period_ending=audit_period_ending))
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
