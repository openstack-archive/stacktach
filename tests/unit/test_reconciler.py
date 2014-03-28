# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import datetime

import mox
import requests

from stacktach import models
from stacktach import reconciler
from stacktach import utils as stackutils
from stacktach.reconciler import exceptions
from stacktach.reconciler import nova
from stacktach.reconciler import utils as rec_utils
from tests.unit import StacktachBaseTestCase
from tests.unit import utils
from tests.unit.utils import INSTANCE_ID_1, INSTANCE_TYPE_ID_1
from tests.unit.utils import INSTANCE_FLAVOR_ID_1
from tests.unit.utils import TENANT_ID_1

region_mapping = {
    'RegionOne.prod.cell1': 'RegionOne',
    'RegionTwo.prod.cell1': 'RegionTwo',
}

DEFAULT_OS_ARCH = 'os_arch'
DEFAULT_OS_DISTRO = 'os_dist'
DEFAULT_OS_VERSION = "1.1"
DEFAULT_RAX_OPTIONS = "rax_ops"


class ReconcilerTestCase(StacktachBaseTestCase):
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

    def _fake_usage(self, is_exists=False, is_deleted=False,
                    mock_deployment=False):
        usage = self.mox.CreateMockAnything()
        usage.id = 1
        beginning_d = utils.decimal_utc()
        usage.instance = INSTANCE_ID_1
        launched_at = beginning_d - (60*60)
        usage.launched_at = launched_at
        usage.instance_type_id = INSTANCE_TYPE_ID_1
        usage.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        usage.tenant = TENANT_ID_1
        usage.os_architecture = DEFAULT_OS_ARCH
        usage.os_distro = DEFAULT_OS_DISTRO
        usage.os_version = DEFAULT_OS_VERSION
        usage.rax_options = DEFAULT_RAX_OPTIONS
        if is_exists:
            usage.deleted_at = None
        if is_deleted:
            usage.deleted_at = beginning_d
        if mock_deployment:
            deployment = self.mox.CreateMockAnything()
            deployment.name = 'RegionOne.prod.cell1'
            usage.deployment().AndReturn(deployment)
        return usage

    def _fake_reconciler_instance(self, uuid=INSTANCE_ID_1, launched_at=None,
                                  deleted_at=None, deleted=False,
                                  instance_type_id=INSTANCE_TYPE_ID_1,
                                  instance_flavor_id=INSTANCE_FLAVOR_ID_1,
                                  tenant=TENANT_ID_1,
                                  os_arch=DEFAULT_OS_ARCH,
                                  os_distro=DEFAULT_OS_DISTRO,
                                  os_verison=DEFAULT_OS_VERSION,
                                  rax_options=DEFAULT_RAX_OPTIONS):
        instance = rec_utils.empty_reconciler_instance()
        instance.update({
            'id': uuid,
            'launched_at': launched_at,
            'deleted_at': deleted_at,
            'deleted': deleted,
            'instance_type_id': instance_type_id,
            'instance_flavor_id': instance_flavor_id,
            'tenant': tenant,
            'os_architecture': os_arch,
            'os_distro': os_distro,
            'os_version': os_verison,
            'rax_options': rax_options,
        })
        return instance

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
        region = self.reconciler._region_for_usage(launch)
        self.assertEqual('RegionOne', region)
        self.mox.VerifyAll()

    def test_region_for_launch_no_mapping(self):
        launch = self.mox.CreateMockAnything()
        deployment = self.mox.CreateMockAnything()
        deployment.name = 'RegionOne.prod.cell2'
        launch.deployment().AndReturn(deployment)
        self.mox.ReplayAll()
        region = self.reconciler._region_for_usage(launch)
        self.assertFalse(region)
        self.mox.VerifyAll()

    def test_region_for_launch_no_raws(self):
        launch = self.mox.CreateMockAnything()
        launch.deployment()
        self.mox.ReplayAll()
        region = self.reconciler._region_for_usage(launch)
        self.assertFalse(region)
        self.mox.VerifyAll()

    def test_missing_exists_for_instance(self):
        launch = self._fake_usage(mock_deployment=True)
        launched_at = launch.launched_at
        deleted_at = launched_at + (60*30)
        period_beginning = deleted_at + 1
        models.InstanceUsage.objects.get(id=launch.id).AndReturn(launch)
        rec_inst = self._fake_reconciler_instance(deleted=True,
                                                  deleted_at=deleted_at)
        self.client.get_instance('RegionOne', INSTANCE_ID_1).AndReturn(rec_inst)
        reconcile_vals = {
            'instance': launch.instance,
            'launched_at': launch.launched_at,
            'deleted_at': deleted_at,
            'instance_type_id': launch.instance_type_id,
            'instance_flavor_id': launch.instance_flavor_id,
            'source': 'reconciler:mocked_client',
            'tenant': TENANT_ID_1,
            'os_architecture': DEFAULT_OS_ARCH,
            'os_distro': DEFAULT_OS_DISTRO,
            'os_version': DEFAULT_OS_VERSION,
            'rax_options': DEFAULT_RAX_OPTIONS,
        }
        result = self.mox.CreateMockAnything()
        models.InstanceReconcile(**reconcile_vals).AndReturn(result)
        result.save()
        self.mox.ReplayAll()
        result = self.reconciler.missing_exists_for_instance(launch.id,
                                                             period_beginning)
        self.assertTrue(result)
        self.mox.VerifyAll()

    def test_missing_exists_for_instance_not_found(self):
        launch_id = 1
        beginning_d = utils.decimal_utc()
        launch = self.mox.CreateMockAnything()
        launch.instance = INSTANCE_ID_1
        launch.launched_at = beginning_d - (60*60)
        launch.instance_flavor_id = INSTANCE_FLAVOR_ID_1
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

    def test_missing_exists_for_instance_region_not_found(self):
        launch_id = 1
        beginning_d = utils.decimal_utc()
        launch = self.mox.CreateMockAnything()
        launch.instance = INSTANCE_FLAVOR_ID_1
        launch.launched_at = beginning_d - (60*60)
        launch.instance_flavor_id = 1
        models.InstanceUsage.objects.get(id=launch_id).AndReturn(launch)
        launch.deployment().AndReturn(None)
        self.mox.ReplayAll()
        result = self.reconciler.missing_exists_for_instance(launch_id,
                                                             beginning_d)
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_failed_validation(self):
        exists = self._fake_usage(is_exists=True, mock_deployment=True)
        launched_at = exists.launched_at
        rec_inst = self._fake_reconciler_instance(launched_at=launched_at)
        self.client.get_instance('RegionOne', INSTANCE_ID_1,
                                 get_metadata=True).AndReturn(rec_inst)
        reconcile_vals = {
            'instance': exists.instance,
            'launched_at': exists.launched_at,
            'deleted_at': exists.deleted_at,
            'instance_type_id': exists.instance_type_id,
            'instance_flavor_id': exists.instance_flavor_id,
            'source': 'reconciler:mocked_client',
            'tenant': TENANT_ID_1,
            'os_architecture': DEFAULT_OS_ARCH,
            'os_distro': DEFAULT_OS_DISTRO,
            'os_version': DEFAULT_OS_VERSION,
            'rax_options': DEFAULT_RAX_OPTIONS,
        }
        result = self.mox.CreateMockAnything()
        models.InstanceReconcile(**reconcile_vals).AndReturn(result)
        result.save()
        self.mox.ReplayAll()
        result = self.reconciler.failed_validation(exists)
        self.assertTrue(result)
        self.mox.VerifyAll()

    def test_failed_validation_deleted(self):
        exists = self._fake_usage(is_exists=True, is_deleted=True,
                                  mock_deployment=True)
        launched_at = exists.launched_at
        deleted_at = exists.deleted_at
        rec_inst = self._fake_reconciler_instance(launched_at=launched_at,
                                                  deleted=True,
                                                  deleted_at=deleted_at)
        self.client.get_instance('RegionOne', INSTANCE_ID_1,
                                 get_metadata=True).AndReturn(rec_inst)
        reconcile_vals = {
            'instance': exists.instance,
            'launched_at': exists.launched_at,
            'deleted_at': exists.deleted_at,
            'instance_type_id': exists.instance_type_id,
            'instance_flavor_id': exists.instance_flavor_id,
            'source': 'reconciler:mocked_client',
            'tenant': TENANT_ID_1,
            'os_architecture': DEFAULT_OS_ARCH,
            'os_distro': DEFAULT_OS_DISTRO,
            'os_version': DEFAULT_OS_VERSION,
            'rax_options': DEFAULT_RAX_OPTIONS,
        }
        result = self.mox.CreateMockAnything()
        models.InstanceReconcile(**reconcile_vals).AndReturn(result)
        result.save()
        self.mox.ReplayAll()
        result = self.reconciler.failed_validation(exists)
        self.assertTrue(result)
        self.mox.VerifyAll()

    def test_failed_validation_deleted_not_matching(self):
        beginning_d = utils.decimal_utc()
        exists = self.mox.CreateMockAnything()
        exists.instance = INSTANCE_ID_1
        launched_at = beginning_d - (60*60)
        exists.launched_at = launched_at
        exists.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        exists.deleted_at = beginning_d
        deployment = self.mox.CreateMockAnything()
        exists.deployment().AndReturn(deployment)
        deployment.name = 'RegionOne.prod.cell1'
        rec_inst = self._fake_reconciler_instance(launched_at=launched_at,
                                                  deleted=True,
                                                  deleted_at=beginning_d+1)
        self.client.get_instance('RegionOne', INSTANCE_ID_1,
                                 get_metadata=True).AndReturn(rec_inst)
        self.mox.ReplayAll()
        result = self.reconciler.failed_validation(exists)
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_failed_validation_deleted_not_deleted_from_client(self):
        beginning_d = utils.decimal_utc()
        exists = self.mox.CreateMockAnything()
        exists.instance = INSTANCE_ID_1
        launched_at = beginning_d - (60*60)
        exists.launched_at = launched_at
        exists.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        exists.deleted_at = beginning_d
        deployment = self.mox.CreateMockAnything()
        exists.deployment().AndReturn(deployment)
        deployment.name = 'RegionOne.prod.cell1'
        rec_inst = self._fake_reconciler_instance(launched_at=launched_at)
        self.client.get_instance('RegionOne', INSTANCE_ID_1,
                                 get_metadata=True).AndReturn(rec_inst)
        self.mox.ReplayAll()
        result = self.reconciler.failed_validation(exists)
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_failed_validation_not_found(self):
        beginning_d = utils.decimal_utc()
        exists = self.mox.CreateMockAnything()
        exists.instance = INSTANCE_ID_1
        launched_at = beginning_d - (60*60)
        exists.launched_at = launched_at
        exists.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        exists.deleted_at = None
        deployment = self.mox.CreateMockAnything()
        exists.deployment().AndReturn(deployment)
        deployment.name = 'RegionOne.prod.cell1'
        ex = exceptions.NotFound()
        self.client.get_instance('RegionOne', INSTANCE_ID_1,
                                 get_metadata=True).AndRaise(ex)
        self.mox.ReplayAll()
        result = self.reconciler.failed_validation(exists)
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_failed_validation_region_not_found(self):
        beginning_d = utils.decimal_utc()
        exists = self.mox.CreateMockAnything()
        exists.instance = INSTANCE_ID_1
        launched_at = beginning_d - (60*60)
        exists.launched_at = launched_at
        exists.instance_flavor_id = INSTANCE_FLAVOR_ID_1
        exists.deleted_at = None
        exists.deployment().AndReturn(None)
        ex = exceptions.NotFound()
        self.mox.ReplayAll()
        result = self.reconciler.failed_validation(exists)
        self.assertFalse(result)
        self.mox.VerifyAll()

    def test_fields_match(self):
        exists = self._fake_usage(is_exists=True)
        kwargs = {'launched_at': exists.launched_at}
        instance = self._fake_reconciler_instance(**kwargs)
        self.mox.ReplayAll()
        match_code = self.reconciler._fields_match(exists, instance)
        self.assertEqual(match_code, 0)
        self.mox.VerifyAll()

    def test_fields_match_field_with_deleted(self):
        exists = self._fake_usage(is_exists=True, is_deleted=True)
        kwargs = {'launched_at': exists.launched_at,
                  'deleted': True,
                  'deleted_at': exists.deleted_at}
        instance = self._fake_reconciler_instance(**kwargs)
        self.mox.ReplayAll()
        match_code = self.reconciler._fields_match(exists, instance)
        self.assertEqual(match_code, 0)
        self.mox.VerifyAll()

    def test_fields_match_field_miss_match(self):
        exists = self._fake_usage(is_exists=True)
        kwargs = {'launched_at': exists.launched_at + 1}
        instance = self._fake_reconciler_instance(**kwargs)
        self.mox.ReplayAll()
        match_code = self.reconciler._fields_match(exists, instance)
        self.assertEqual(match_code, 1)
        self.mox.VerifyAll()

    def test_fields_match_field_with_deleted_miss_match(self):
        exists = self._fake_usage(is_exists=True, is_deleted=True)
        kwargs = {'launched_at': exists.launched_at,
                  'deleted': True,
                  'deleted_at': exists.deleted_at+1}
        instance = self._fake_reconciler_instance(**kwargs)
        self.mox.ReplayAll()
        match_code = self.reconciler._fields_match(exists, instance)
        self.assertEqual(match_code, 2)
        self.mox.VerifyAll()

    def test_fields_match_field_not_deleted_in_nova(self):
        exists = self._fake_usage(is_exists=True, is_deleted=True)
        kwargs = {'launched_at': exists.launched_at}
        instance = self._fake_reconciler_instance(**kwargs)
        self.mox.ReplayAll()
        match_code = self.reconciler._fields_match(exists, instance)
        self.assertEqual(match_code, 3)
        self.mox.VerifyAll()

    def test_fields_match_field_not_deleted_in_exists(self):
        exists = self._fake_usage(is_exists=True)
        kwargs = {'launched_at': exists.launched_at,
                  'deleted': True,
                  'deleted_at': exists.launched_at + 1}
        instance = self._fake_reconciler_instance(**kwargs)
        self.mox.ReplayAll()
        match_code = self.reconciler._fields_match(exists, instance)
        self.assertEqual(match_code, 4)
        self.mox.VerifyAll()


json_bridge_config = {
    'url': 'http://json_bridge.example.com/query/',
    'username': 'user',
    'password': 'pass',
    'databases': {
        'RegionOne': 'nova',
    }
}


class NovaJSONBridgeClientTestCase(StacktachBaseTestCase):
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
                       terminated_at=None, deleted=0,
                       instance_type_id=INSTANCE_TYPE_ID_1,
                       instance_flavor_id=INSTANCE_FLAVOR_ID_1,
                       project_id=TENANT_ID_1):
        return {
            'uuid': uuid,
            'launched_at': launched_at,
            'terminated_at': terminated_at,
            'deleted': deleted,
            'instance_type_id': instance_type_id,
            'flavorid': instance_flavor_id,
            'project_id': project_id
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
        self.assertEqual(instance['id'], INSTANCE_ID_1 )
        self.assertEqual(instance['instance_type_id'], INSTANCE_TYPE_ID_1)
        self.assertEqual(instance['instance_flavor_id'], INSTANCE_FLAVOR_ID_1)
        launched_at_dec = stackutils.str_time_to_unix(launched_at)
        self.assertEqual(instance['launched_at'], launched_at_dec)
        terminated_at_dec = stackutils.str_time_to_unix(terminated_at)
        self.assertEqual(instance['deleted_at'], terminated_at_dec)
        self.assertTrue(instance['deleted'])
        self.mox.VerifyAll()

    def _fake_metadata(self):
        metadata = [
            {'key': 'image_org.openstack__1__architecture',
             'value': DEFAULT_OS_ARCH},
            {'key': 'image_org.openstack__1__os_distro',
             'value': DEFAULT_OS_DISTRO},
            {'key': 'image_org.openstack__1__os_version',
             'value': DEFAULT_OS_VERSION},
            {'key': 'image_com.rackspace__1__options',
             'value': DEFAULT_RAX_OPTIONS},
        ]
        return metadata

    def test_get_instance_with_metadata(self):
        launched_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
        launched_at = str(launched_at)
        terminated_at = str(datetime.datetime.utcnow())
        results = [self._fake_instance(launched_at=launched_at,
                                       terminated_at=terminated_at,
                                       deleted=True)]
        metadata_results = self._fake_metadata()
        self.mock_for_query('nova', nova.GET_INSTANCE_QUERY % INSTANCE_ID_1,
                            results)
        self.mock_for_query('nova',
                            nova.GET_INSTANCE_SYSTEM_METADATA % INSTANCE_ID_1,
                            metadata_results)
        self.mox.ReplayAll()
        instance = self.client.get_instance('RegionOne', INSTANCE_ID_1,
                                            get_metadata=True)
        self.assertIsNotNone(instance)
        self.assertEqual(instance['id'], INSTANCE_ID_1)
        self.assertEqual(instance['instance_flavor_id'], INSTANCE_FLAVOR_ID_1)
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
