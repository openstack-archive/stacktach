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
from novaclient.exceptions import NotFound
from novaclient.v1_1 import client as nova_client

from stacktach import models
from stacktach import reconciler
import utils
from utils import INSTANCE_ID_1
from utils import REQUEST_ID_1


config = {
    'nova': {
        'RegionOne': {
            'username': 'demo',
            'project_id': '111111',
            'api_key': 'some_key',
            'auth_url': 'https://identity.example.com/v2.0',
            'auth_system': 'keystone',
        },
        'RegionTwo': {
            'username': 'demo',
            'project_id': '111111',
            'api_key': 'some_key',
            'auth_url': 'https://identity.example.com/v2.0',
            'auth_system': 'keystone',
        },

    },
    'region_mapping_loc': '/etc/stacktach/region_mapping.json',
    'flavor_mapping_loc': '/etc/stacktach/flavor_mapping.json',
}

region_mapping = {
    'RegionOne.prod.cell1': 'RegionOne',
    'RegionTwo.prod.cell1': 'RegionTwo',
}


class ReconcilerTestCase(unittest.TestCase):
    def setUp(self):
        self.reconciler = reconciler.Reconciler(config,
                                                region_mapping=region_mapping)
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
        self.mox.StubOutWithMock(nova_client, 'Client', use_mock_anything=True)

    def tearDown(self):
        self.mox.UnsetStubs()

    def _mocked_nova_client(self):
        nova = self.mox.CreateMockAnything()
        nova.servers = self.mox.CreateMockAnything()
        return nova

    def test_region_for_launch(self):
        launch = self.mox.CreateMockAnything()
        launch.request_id = REQUEST_ID_1
        result = self.mox.CreateMockAnything()
        models.RawData.objects.filter(request_id=REQUEST_ID_1)\
                              .AndReturn(result)
        result.count().AndReturn(1)
        raw = self.mox.CreateMockAnything()
        raw.deployment = self.mox.CreateMockAnything()
        raw.deployment.name = 'RegionOne.prod.cell1'
        result[0].AndReturn(raw)
        self.mox.ReplayAll()
        region = self.reconciler._region_for_launch(launch)
        self.assertEqual('RegionOne', region)
        self.mox.VerifyAll()

    def test_region_for_launch_no_mapping(self):
        launch = self.mox.CreateMockAnything()
        launch.request_id = REQUEST_ID_1
        result = self.mox.CreateMockAnything()
        models.RawData.objects.filter(request_id=REQUEST_ID_1)\
                              .AndReturn(result)
        result.count().AndReturn(1)
        raw = self.mox.CreateMockAnything()
        raw.deployment = self.mox.CreateMockAnything()
        raw.deployment.name = 'RegionOne.prod.cell2'
        result[0].AndReturn(raw)
        self.mox.ReplayAll()
        region = self.reconciler._region_for_launch(launch)
        self.assertFalse(region)
        self.mox.VerifyAll()

    def test_region_for_launch_no_raws(self):
        launch = self.mox.CreateMockAnything()
        launch.request_id = REQUEST_ID_1
        result = self.mox.CreateMockAnything()
        models.RawData.objects.filter(request_id=REQUEST_ID_1)\
                              .AndReturn(result)
        result.count().AndReturn(0)
        self.mox.ReplayAll()
        region = self.reconciler._region_for_launch(launch)
        self.assertFalse(region)
        self.mox.VerifyAll()

    def test_get_nova(self):
        expected_client = self._mocked_nova_client
        nova_client.Client('demo', 'some_key', '111111',
                           auth_url='https://identity.example.com/v2.0',
                           auth_system='keystone').AndReturn(expected_client)
        self.mox.ReplayAll()
        client = self.reconciler._get_nova('RegionOne')
        self.assertEqual(expected_client, client)
        self.mox.VerifyAll()

    def test_get_nova_already_created(self):
        expected_client = self.mox.CreateMockAnything()
        nova_client.Client('demo', 'some_key', '111111',
                           auth_url='https://identity.example.com/v2.0',
                           auth_system='keystone').AndReturn(expected_client)
        self.mox.ReplayAll()
        self.reconciler._get_nova('RegionOne')
        client = self.reconciler._get_nova('RegionOne')
        self.assertEqual(expected_client, client)
        self.mox.VerifyAll()

    def test_reconcile_from_api(self):
        deleted_at = datetime.datetime.utcnow()
        launched_at = deleted_at - datetime.timedelta(hours=4)
        launch = self.mox.CreateMockAnything()
        launch.instance = INSTANCE_ID_1
        launch.launched_at = utils.decimal_utc(launched_at)
        launch.instance_type_id = 1
        server = self.mox.CreateMockAnything()
        server.id = INSTANCE_ID_1
        server._info = {
            'OS-INST-USG:terminated_at': str(deleted_at),
        }
        values = {
            'instance': INSTANCE_ID_1,
            'instance_type_id': 1,
            'launched_at': utils.decimal_utc(launched_at),
            'deleted_at': utils.decimal_utc(deleted_at),
            'source': 'reconciler:nova_api'
        }
        result = self.mox.CreateMockAnything()
        models.InstanceReconcile(**values).AndReturn(result)
        result.save()
        self.mox.ReplayAll()
        self.reconciler._reconcile_from_api(launch, server)
        self.mox.VerifyAll()

    def test_reconcile_from_api_not_found(self):
        deleted_at = datetime.datetime.utcnow()
        launched_at = deleted_at - datetime.timedelta(hours=4)
        launch = self.mox.CreateMockAnything()
        launch.instance = INSTANCE_ID_1
        launch.launched_at = utils.decimal_utc(launched_at)
        launch.instance_type_id = 1
        values = {
            'instance': INSTANCE_ID_1,
            'instance_type_id': 1,
            'launched_at': utils.decimal_utc(launched_at),
            'deleted_at': 1,
            'source': 'reconciler:nova_api:not_found'
        }
        result = self.mox.CreateMockAnything()
        models.InstanceReconcile(**values).AndReturn(result)
        result.save()
        self.mox.ReplayAll()
        self.reconciler._reconcile_from_api_not_found(launch)
        self.mox.VerifyAll()

    def test_missing_exists_for_instance(self):
        now = datetime.datetime.utcnow()
        deleted_at_dt = now - datetime.timedelta(days=2)
        beginning_dt = now - datetime.timedelta(days=1)
        beginning_dec = utils.decimal_utc(beginning_dt)

        launch = self.mox.CreateMockAnything()
        launch.instance = INSTANCE_ID_1
        models.InstanceUsage.objects.get(1).AndReturn(launch)
        self.mox.StubOutWithMock(self.reconciler, '_region_for_launch')
        self.reconciler._region_for_launch(launch).AndReturn('RegionOne')

        self.mox.StubOutWithMock(self.reconciler, '_get_nova')
        nova = self._mocked_nova_client()
        self.reconciler._get_nova('RegionOne').AndReturn(nova)
        server = self.mox.CreateMockAnything()
        server._info = {
            'OS-INST-USG:terminated_at': str(deleted_at_dt),
        }
        nova.servers.get(INSTANCE_ID_1).AndReturn(server)

        self.mox.StubOutWithMock(self.reconciler, '_reconcile_from_api')
        self.reconciler._reconcile_from_api(launch, server)

        self.mox.ReplayAll()
        result = self.reconciler.missing_exists_for_instance(1, beginning_dec)
        self.assertTrue(result)
        self.mox.VerifyAll()

    def test_missing_exists_for_instance_deleted_too_soon(self):
        now = datetime.datetime.utcnow()
        deleted_at_dt = now - datetime.timedelta(hours=4)
        beginning_dt = now - datetime.timedelta(days=1)
        beginning_dec = utils.decimal_utc(beginning_dt)

        launch = self.mox.CreateMockAnything()
        launch.instance = INSTANCE_ID_1
        models.InstanceUsage.objects.get(1).AndReturn(launch)
        self.mox.StubOutWithMock(self.reconciler, '_region_for_launch')
        self.reconciler._region_for_launch(launch).AndReturn('RegionOne')

        self.mox.StubOutWithMock(self.reconciler, '_get_nova')
        nova = self._mocked_nova_client()
        self.reconciler._get_nova('RegionOne').AndReturn(nova)
        server = self.mox.CreateMockAnything()
        server._info = {
            'OS-INST-USG:terminated_at': str(deleted_at_dt),
        }
        nova.servers.get(INSTANCE_ID_1).AndReturn(server)

        self.mox.StubOutWithMock(self.reconciler, '_reconcile_from_api')

        self.mox.ReplayAll()
        result = self.reconciler.missing_exists_for_instance(1, beginning_dec)
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_missing_exists_for_instance_not_deleted(self):
        now = datetime.datetime.utcnow()
        beginning_dt = now - datetime.timedelta(days=1)
        beginning_dec = utils.decimal_utc(beginning_dt)

        launch = self.mox.CreateMockAnything()
        launch.instance = INSTANCE_ID_1
        models.InstanceUsage.objects.get(1).AndReturn(launch)
        self.mox.StubOutWithMock(self.reconciler, '_region_for_launch')
        self.reconciler._region_for_launch(launch).AndReturn('RegionOne')

        self.mox.StubOutWithMock(self.reconciler, '_get_nova')
        nova = self._mocked_nova_client()
        self.reconciler._get_nova('RegionOne').AndReturn(nova)
        server = self.mox.CreateMockAnything()
        server._info = {}
        nova.servers.get(INSTANCE_ID_1).AndReturn(server)

        self.mox.StubOutWithMock(self.reconciler, '_reconcile_from_api')

        self.mox.ReplayAll()
        result = self.reconciler.missing_exists_for_instance(1, beginning_dec)
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_missing_exists_for_instance_not_found(self):
        now = datetime.datetime.utcnow()
        beginning_dt = now - datetime.timedelta(days=1)
        beginning_dec = utils.decimal_utc(beginning_dt)

        launch = self.mox.CreateMockAnything()
        launch.instance = INSTANCE_ID_1
        models.InstanceUsage.objects.get(1).AndReturn(launch)
        self.mox.StubOutWithMock(self.reconciler, '_region_for_launch')
        self.reconciler._region_for_launch(launch).AndReturn('RegionOne')

        self.mox.StubOutWithMock(self.reconciler, '_get_nova')
        nova = self._mocked_nova_client()
        self.reconciler._get_nova('RegionOne').AndReturn(nova)

        nova.servers.get(INSTANCE_ID_1).AndRaise(NotFound(404))

        self.mox.StubOutWithMock(self.reconciler,
                                 '_reconcile_from_api_not_found')
        self.reconciler._reconcile_from_api_not_found(launch)

        self.mox.ReplayAll()
        result = self.reconciler.missing_exists_for_instance(1, beginning_dec)
        self.assertTrue(result)
        self.mox.VerifyAll()
