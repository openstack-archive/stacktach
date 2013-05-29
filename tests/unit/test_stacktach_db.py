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
import unittest

import mox

from stacktach import db
from stacktach import stacklog
from stacktach import models


class StacktachDBTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.log = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(stacklog, 'get_logger')
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

    def setup_mock_log(self, name=None):
        if name is None:
            stacklog.get_logger(name=mox.IgnoreArg()).AndReturn(self.log)
        else:
            stacklog.get_logger(name=name).AndReturn(self.log)

    def test_safe_get(self):
        Model = self.mox.CreateMockAnything()
        Model.objects = self.mox.CreateMockAnything()
        filters = {'field1': 'value1', 'field2': 'value2'}
        results = self.mox.CreateMockAnything()
        Model.objects.filter(**filters).AndReturn(results)
        results.count().AndReturn(1)
        object = self.mox.CreateMockAnything()
        results[0].AndReturn(object)
        self.mox.ReplayAll()
        returned = db._safe_get(Model, **filters)
        self.assertEqual(returned, object)
        self.mox.VerifyAll()

    def test_safe_get_no_results(self):
        Model = self.mox.CreateMockAnything()
        Model.__name__ = 'Model'
        Model.objects = self.mox.CreateMockAnything()
        filters = {'field1': 'value1', 'field2': 'value2'}
        results = self.mox.CreateMockAnything()
        Model.objects.filter(**filters).AndReturn(results)
        results.count().AndReturn(0)
        log = self.mox.CreateMockAnything()
        self.setup_mock_log()
        self.log.warn('No records found for Model get.')
        self.mox.ReplayAll()
        returned = db._safe_get(Model, **filters)
        self.assertEqual(returned, None)
        self.mox.VerifyAll()

    def test_safe_get_multiple_results(self):
        Model = self.mox.CreateMockAnything()
        Model.__name__ = 'Model'
        Model.objects = self.mox.CreateMockAnything()
        filters = {'field1': 'value1', 'field2': 'value2'}
        results = self.mox.CreateMockAnything()
        Model.objects.filter(**filters).AndReturn(results)
        results.count().AndReturn(2)
        self.setup_mock_log()
        self.log.warn('Multiple records found for Model get.')
        object = self.mox.CreateMockAnything()
        results[0].AndReturn(object)
        self.mox.ReplayAll()
        returned = db._safe_get(Model, **filters)
        self.assertEqual(returned, object)
        self.mox.VerifyAll()

    def test_get_or_create_deployment(self):
        deployment = self.mox.CreateMockAnything()
        models.Deployment.objects.get_or_create(name='test').AndReturn(deployment)
        self.mox.ReplayAll()
        returned = db.get_or_create_deployment('test')
        self.assertEqual(returned, deployment)
        self.mox.VerifyAll()

    def _test_db_create_func(self, Model, func):
        params = {'field1': 'value1', 'field2': 'value2'}
        object = self.mox.CreateMockAnything()
        Model(**params).AndReturn(object)
        self.mox.ReplayAll()
        returned = func(**params)
        self.assertEqual(returned, object)
        self.mox.VerifyAll()

    def test_create_rawdata(self):
        self._test_db_create_func(models.RawData, db.create_rawdata)

    def test_create_lifecycle(self):
        self._test_db_create_func(models.Lifecycle, db.create_lifecycle)

    def test_create_timing(self):
        self._test_db_create_func(models.Timing, db.create_timing)

    def test_create_request_tracker(self):
        self._test_db_create_func(models.RequestTracker,
                                  db.create_request_tracker)

    def test_create_instance_usage(self):
        self._test_db_create_func(models.InstanceUsage,
                                  db.create_instance_usage)

    def test_create_instance_delete(self):
        self._test_db_create_func(models.InstanceDeletes,
                                  db.create_instance_delete)

    def test_create_instance_exists(self):
        self._test_db_create_func(models.InstanceExists,
                                  db.create_instance_exists)

    def _test_db_find_func(self, Model, func, select_related=True):
        params = {'field1': 'value1', 'field2': 'value2'}
        results = self.mox.CreateMockAnything()
        if select_related:
            Model.objects.select_related().AndReturn(results)
            results.filter(**params).AndReturn(results)
        else:
            Model.objects.filter(**params).AndReturn(results)
        self.mox.ReplayAll()
        returned = func(**params)
        self.assertEqual(returned, results)
        self.mox.VerifyAll()

    def test_find_lifecycles(self):
        self._test_db_find_func(models.Lifecycle, db.find_lifecycles)

    def test_find_timings(self):
        self._test_db_find_func(models.Timing, db.find_timings)

    def test_find_request_trackers(self):
        self._test_db_find_func(models.RequestTracker,
                                db.find_request_trackers,
                                select_related=False)

    def _test_db_get_or_create_func(self, Model, func):
        params = {'field1': 'value1', 'field2': 'value2'}
        object = self.mox.CreateMockAnything()
        Model.objects.get_or_create(**params).AndReturn(object)
        self.mox.ReplayAll()
        returned = func(**params)
        self.assertEqual(returned, object)
        self.mox.VerifyAll()

    def test_get_or_create_instance_usage(self):
        self._test_db_get_or_create_func(models.InstanceUsage,
                                         db.get_or_create_instance_usage)

    def test_get_or_create_instance_delete(self):
        self._test_db_get_or_create_func(models.InstanceDeletes,
                                         db.get_or_create_instance_delete)

    def test_get_instance_usage(self):
        filters = {'field1': 'value1', 'field2': 'value2'}
        results = self.mox.CreateMockAnything()
        models.InstanceUsage.objects.filter(**filters).AndReturn(results)
        results.count().AndReturn(1)
        usage = self.mox.CreateMockAnything()
        results[0].AndReturn(usage)
        self.mox.ReplayAll()
        returned = db.get_instance_usage(**filters)
        self.assertEqual(returned, usage)
        self.mox.VerifyAll()

    def test_get_instance_delete(self):
        filters = {'field1': 'value1', 'field2': 'value2'}
        results = self.mox.CreateMockAnything()
        models.InstanceDeletes.objects.filter(**filters).AndReturn(results)
        results.count().AndReturn(1)
        usage = self.mox.CreateMockAnything()
        results[0].AndReturn(usage)
        self.mox.ReplayAll()
        returned = db.get_instance_delete(**filters)
        self.assertEqual(returned, usage)
        self.mox.VerifyAll()

    def test_save(self):
        o = self.mox.CreateMockAnything()
        o.save()
        self.mox.ReplayAll()
        db.save(o)
        self.mox.VerifyAll()
