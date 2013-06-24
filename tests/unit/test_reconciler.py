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
import requests

from stacktach import models
from stacktach import reconciler
from stacktach import utils as stackutils
from stacktach.reconciler import exceptions
from stacktach.reconciler import nova
from tests.unit import utils
from tests.unit.utils import INSTANCE_ID_1

region_mapping = {
    'RegionOne.prod.cell1': 'RegionOne',
    'RegionTwo.prod.cell1': 'RegionTwo',
}


class ReconcilerTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.client = self.mox.CreateMockAnything()
        self.client.src_str = 'mocked_client'
        self.reconciler = reconciler.Reconciler({},
                                                client=self.client,
                                                region_mapping=region_mapping)
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
        self.mox.StubOutWithMock(models, 'InstanceReconcile',
                                 use_mock_anything=True)
        models.InstanceReconcile.objects = self.mox.CreateMockAnything()
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

    def _fake_reconciler_instance(self, uuid=INSTANCE_ID_1, launched_at=None,
                                  deleted_at=None, deleted=False,
                                  instance_type_id=1):
        return {
            'id': uuid,
            'launched_at': launched_at,
            'deleted_at': deleted_at,
            'deleted': deleted,
            'instance_type_id': instance_type_id
        }

    def test_load_client_json_bridge(self):
        mock_config = self.mox.CreateMockAnything()
        config = {'client_class': 'JSONBridgeClient', 'client': mock_config}
        nova.JSONBridgeClient(mock_config)
        self.mox.ReplayAll()
        reconciler.Reconciler.load_client(config)
        self.mox.VerifyAll()

    def test_load_client_no_class_loads_default_class(self):
        mock_config = self.mox.CreateMockAnything()
        config = {'client': mock_config}
        nova.JSONBridgeClient(mock_config)
        self.mox.ReplayAll()
        reconciler.Reconciler.load_client(config)
        self.mox.VerifyAll()

    def test_load_client_incorrect_class_loads_default_class(self):
        mock_config = self.mox.CreateMockAnything()
        config = {'client_class': 'BadConfigValue', 'client': mock_config}
        nova.JSONBridgeClient(mock_config)
        self.mox.ReplayAll()
        reconciler.Reconciler.load_client(config)
        self.mox.VerifyAll()

    def test_region_for_launch(self):
        launch = self.mox.CreateMockAnything()
        deployment = self.mox.CreateMockAnything()
        deployment.name = 'RegionOne.prod.cell1'
        launch.deployment().AndReturn(deployment)
        self.mox.ReplayAll()
        region = self.reconciler._region_for_launch(launch)
        self.assertEqual('RegionOne', region)
        self.mox.VerifyAll()

    def test_region_for_launch_no_mapping(self):
        launch = self.mox.CreateMockAnything()
        deployment = self.mox.CreateMockAnything()
        deployment.name = 'RegionOne.prod.cell2'
        launch.deployment().AndReturn(deployment)
        self.mox.ReplayAll()
        region = self.reconciler._region_for_launch(launch)
        self.assertFalse(region)
        self.mox.VerifyAll()

    def test_region_for_launch_no_raws(self):
        launch = self.mox.CreateMockAnything()
        launch.deployment()
        self.mox.ReplayAll()
        region = self.reconciler._region_for_launch(launch)
        self.assertFalse(region)
        self.mox.VerifyAll()

    def test_missing_exists_for_instance(self):
        launch_id = 1
        beginning_d = utils.decimal_utc()
        launch = self.mox.CreateMockAnything()
        launch.instance = INSTANCE_ID_1
        launch.launched_at = beginning_d - (60*60)
        launch.instance_type_id = 1
        models.InstanceUsage.objects.get(id=launch_id).AndReturn(launch)
        deployment = self.mox.CreateMockAnything()
        launch.deployment().AndReturn(deployment)
        deployment.name = 'RegionOne.prod.cell1'
        deleted_at = beginning_d - (60*30)
        rec_inst = self._fake_reconciler_instance(deleted=True,
                                                  deleted_at=deleted_at)
        self.client.get_instance('RegionOne', INSTANCE_ID_1).AndReturn(rec_inst)
        reconcile_vals = {
            'instance': launch.instance,
            'launched_at': launch.launched_at,
            'deleted_at': deleted_at,
            'instance_type_id': launch.instance_type_id,
            'source': 'reconciler:mocked_client'
        }
        result = self.mox.CreateMockAnything()
        models.InstanceReconcile(**reconcile_vals).AndReturn(result)
        result.save()
        self.mox.ReplayAll()
        result = self.reconciler.missing_exists_for_instance(launch_id,
                                                             beginning_d)
        self.assertTrue(result)
        self.mox.VerifyAll()

    def test_missing_exists_for_instance_not_found(self):
        launch_id = 1
        beginning_d = utils.decimal_utc()
        launch = self.mox.CreateMockAnything()
        launch.instance = INSTANCE_ID_1
        launch.launched_at = beginning_d - (60*60)
        launch.instance_type_id = 1
        models.InstanceUsage.objects.get(id=launch_id).AndReturn(launch)
        deployment = self.mox.CreateMockAnything()
        launch.deployment().AndReturn(deployment)
        deployment.name = 'RegionOne.prod.cell1'
        ex = exceptions.NotFound()
        self.client.get_instance('RegionOne', INSTANCE_ID_1).AndRaise(ex)
        self.mox.ReplayAll()
        result = self.reconciler.missing_exists_for_instance(launch_id,
                                                             beginning_d)
        self.assertFalse(result)
        self.mox.VerifyAll()


json_bridge_config = {
    'url': 'http://json_bridge.example.com/query/',
    'username': 'user',
    'password': 'pass',
    'databases': {
        'RegionOne': 'nova',
    }
}


class NovaJSONBridgeClientTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()
        self.client = nova.JSONBridgeClient(json_bridge_config)
        self.mox.StubOutWithMock(requests, 'post')

    def tearDown(self):
        self.mox.UnsetStubs()

    def mock_for_query(self, database, query, results):
        url = json_bridge_config['url'] + database
        data = {'sql': query}
        auth = (json_bridge_config['username'], json_bridge_config['password'])
        result = {'result': results}
        response = self.mox.CreateMockAnything()
        requests.post(url, data, auth=auth, verify=False)\
                .AndReturn(response)
        response.json().AndReturn(result)

    def _fake_instance(self, uuid=INSTANCE_ID_1, launched_at=None,
                      terminated_at=None, deleted=0, instance_type_id=1):
        return {
            'uuid': uuid,
            'launched_at': launched_at,
            'terminated_at': terminated_at,
            'deleted': deleted,
            'instance_type_id': instance_type_id
        }

    def test_get_instance(self):
        launched_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
        launched_at = str(launched_at)
        terminated_at = str(datetime.datetime.utcnow())
        results = [self._fake_instance(launched_at=launched_at,
                                       terminated_at=terminated_at,
                                       deleted=True)]
        self.mock_for_query('nova', nova.GET_INSTANCE_QUERY % INSTANCE_ID_1,
                            results)
        self.mox.ReplayAll()
        instance = self.client.get_instance('RegionOne', INSTANCE_ID_1)
        self.assertIsNotNone(instance)
        self.assertEqual(instance['id'], INSTANCE_ID_1)
        self.assertEqual(instance['instance_type_id'], 1)
        launched_at_dec = stackutils.str_time_to_unix(launched_at)
        self.assertEqual(instance['launched_at'], launched_at_dec)
        terminated_at_dec = stackutils.str_time_to_unix(terminated_at)
        self.assertEqual(instance['deleted_at'], terminated_at_dec)
        self.assertTrue(instance['deleted'])
        self.mox.VerifyAll()

    def test_get_instance_not_found(self):
        self.mock_for_query('nova', nova.GET_INSTANCE_QUERY % INSTANCE_ID_1,
                            [])
        self.mox.ReplayAll()
        self.assertRaises(exceptions.NotFound, self.client.get_instance,
                          'RegionOne', INSTANCE_ID_1)
        self.mox.VerifyAll()
