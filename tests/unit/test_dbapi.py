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
import json

from django.db.models import Count
from django.db.models import FieldDoesNotExist
from django.db import transaction
import mox

from stacktach import dbapi
from stacktach import models
from stacktach import utils as stacktach_utils
from tests.unit import StacktachBaseTestCase
import utils
from utils import INSTANCE_ID_1
from utils import MESSAGE_ID_1
from utils import MESSAGE_ID_2
from utils import MESSAGE_ID_3
from utils import MESSAGE_ID_4


class Length(mox.Comparator):
    def __init__(self, l):
        self._len = l

    def equals(self, rhs):
        return self._len == len(rhs)

    def __repr__(self):
        return "<sequence with len %s >" % self._len


class DBAPITestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        dne_exception = models.InstanceExists.DoesNotExist
        mor_exception = models.InstanceExists.MultipleObjectsReturned
        self.mox.StubOutWithMock(models, 'RawData',
                                 use_mock_anything=True)
        self.mox.StubOutWithMock(models, 'InstanceExists',
                                 use_mock_anything=True)
        self.mox.StubOutWithMock(models, 'ImageExists',
                                 use_mock_anything=True)
        models.RawData.objects = self.mox.CreateMockAnything()
        models.InstanceExists._meta = self.mox.CreateMockAnything()
        models.ImageExists._meta = self.mox.CreateMockAnything()
        models.InstanceExists.objects = self.mox.CreateMockAnything()
        models.ImageExists.objects = self.mox.CreateMockAnything()
        models.InstanceExists.DoesNotExist = dne_exception
        models.ImageExists.DoesNotExist = dne_exception
        models.InstanceExists.MultipleObjectsReturned = mor_exception
        models.ImageExists.MultipleObjectsReturned = mor_exception

    def tearDown(self):
        self.mox.UnsetStubs()

    def make_fake_model(self):
        fake_model = self.mox.CreateMockAnything()
        fake_meta = self.mox.CreateMockAnything()
        fake_model._meta = fake_meta
        fake_orm = self.mox.CreateMockAnything()
        fake_model.objects = fake_orm
        return fake_model

    def test_get_filter_args(self):
        start_time = datetime.datetime.utcnow()
        start_decimal = utils.decimal_utc(start_time)
        end_time = start_time + datetime.timedelta(days=1)
        end_decimal = utils.decimal_utc(end_time)
        fake_request = self.mox.CreateMockAnything()
        fake_model = self.make_fake_model()
        fake_model._meta.get_field_by_name('launched_at')
        fake_model._meta.get_field_by_name('launched_at')
        fake_request.GET = {'instance': INSTANCE_ID_1,
                            'launched_at_min': str(start_time),
                            'launched_at_max': str(end_time)}
        self.mox.ReplayAll()

        filter_args = dbapi._get_filter_args(fake_model, fake_request)

        self.mox.VerifyAll()
        self.assertEquals(filter_args['instance'], INSTANCE_ID_1)
        self.assertEquals(filter_args.get('launched_at__gte'),
                          start_decimal)
        self.assertEquals(filter_args.get('launched_at__lte'),
                          end_decimal)

    def test_get_filter_args_bad_uuid(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'instance': 'obviouslybaduuid'}
        self.mox.ReplayAll()

        self.assertRaises(dbapi.BadRequestException, dbapi._get_filter_args,
                          fake_model, fake_request)

        self.mox.VerifyAll()

    def test_get_filter_args_bad_min_value(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'launched_at_min': 'obviouslybaddatetime'}
        fake_model = self.make_fake_model()
        fake_model._meta.get_field_by_name('launched_at')
        self.mox.ReplayAll()

        self.assertRaises(dbapi.BadRequestException, dbapi._get_filter_args,
                          fake_model, fake_request)

        self.mox.VerifyAll()

    def test_get_filter_args_bad_max_value(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'launched_at_max': 'obviouslybaddatetime'}
        fake_model = self.make_fake_model()
        fake_model._meta.get_field_by_name('launched_at')
        self.mox.ReplayAll()

        self.assertRaises(dbapi.BadRequestException, dbapi._get_filter_args,
                          fake_model, fake_request)

        self.mox.VerifyAll()

    def test_get_filter_args_bad_range_key(self):
        start_time = datetime.datetime.utcnow()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'somebadfield_max': str(start_time)}
        fake_model = self.make_fake_model()
        fake_model._meta.get_field_by_name('somebadfield') \
            .AndRaise(FieldDoesNotExist())
        self.mox.ReplayAll()

        self.assertRaises(dbapi.BadRequestException, dbapi._get_filter_args,
                          fake_model, fake_request)

        self.mox.VerifyAll()

    def test_get_db_objects(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn({})
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.all().AndReturn(result)
        result.order_by('-id').AndReturn(result)
        s = slice(None, dbapi.DEFAULT_LIMIT, None)
        result.__getitem__(s).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_desc(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'direction': 'desc'}
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn({})
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.all().AndReturn(result)
        result.order_by('-id').AndReturn(result)
        s = slice(None, dbapi.DEFAULT_LIMIT, None)
        result.__getitem__(s).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_asc(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'direction': 'asc'}
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn({})
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.all().AndReturn(result)
        result.order_by('id').AndReturn(result)
        s = slice(None, dbapi.DEFAULT_LIMIT, None)
        result.__getitem__(s).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_limit(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'limit': '1'}
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn({})
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.all().AndReturn(result)
        result.order_by('-id').AndReturn(result)
        result.__getitem__(slice(None, 1, None)).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_hard_limit(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'limit': str(dbapi.HARD_LIMIT + 1)}
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn({})
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.all().AndReturn(result)
        result.order_by('-id').AndReturn(result)
        s = slice(None, dbapi.HARD_LIMIT, None)
        result.__getitem__(s).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_offset(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'offset': '1'}
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn({})
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.all().AndReturn(result)
        result.order_by('-id').AndReturn(result)
        result.__getslice__(1, dbapi.DEFAULT_LIMIT + 1).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_offset_and_limit(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'offset': '2', 'limit': '2'}
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn({})
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.all().AndReturn(result)
        result.order_by('-id').AndReturn(result)
        result.__getslice__(2, 4).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_with_filter(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        filters = {'instance': INSTANCE_ID_1}
        fake_request.GET = filters
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn(filters)
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.filter(**filters).AndReturn(result)
        result.order_by('-id').AndReturn(result)
        s = slice(None, dbapi.DEFAULT_LIMIT, None)
        result.__getitem__(s).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_with_custom_filter(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        filters = {'instance': INSTANCE_ID_1}
        custom_filters = {'raw': {'raw__id': 1}}
        fake_request.GET = filters
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=custom_filters).AndReturn(
            filters)
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        all_filters = {}
        all_filters.update(filters)
        all_filters.update(custom_filters['raw'])
        fake_model.objects.filter(**all_filters).AndReturn(result)
        result.order_by('-id').AndReturn(result)
        s = slice(None, dbapi.DEFAULT_LIMIT, None)
        result.__getitem__(s).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id',
                                            custom_filters=custom_filters)
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_list_usage_exists_no_custom_filters_for_nova(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        objects = self.mox.CreateMockAnything()
        dbapi.get_db_objects(models.InstanceExists, fake_request, 'id',
                             custom_filters={}).AndReturn(objects)
        self.mox.StubOutWithMock(dbapi, '_convert_model_list')
        dbapi._convert_model_list(objects, dbapi._exists_extra_values)
        self.mox.ReplayAll()
        resp = dbapi.list_usage_exists(fake_request)
        self.assertEqual(resp.status_code, 200)
        self.mox.VerifyAll()

    def test_list_usage_exists_no_custom_filters_for_glance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {}
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        objects = self.mox.CreateMockAnything()
        dbapi.get_db_objects(models.ImageExists, fake_request, 'id',
                             custom_filters={}).AndReturn(objects)
        self.mox.StubOutWithMock(dbapi, '_convert_model_list')
        dbapi._convert_model_list(objects, dbapi._exists_extra_values)
        self.mox.ReplayAll()
        resp = dbapi.list_usage_exists_glance(fake_request)
        self.assertEqual(resp.status_code, 200)
        self.mox.VerifyAll()

    def test_list_usage_exists_with_received_min(self):
        fake_request = self.mox.CreateMockAnything()
        date = str(datetime.datetime.utcnow())
        fake_request.GET = {'received_min': date}
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        unix_date = stacktach_utils.str_time_to_unix(date)
        custom_filters = {'received_min': {'raw__when__gte': unix_date}}
        objects = self.mox.CreateMockAnything()
        dbapi.get_db_objects(models.InstanceExists, fake_request, 'id',
                             custom_filters=custom_filters).AndReturn(objects)
        self.mox.StubOutWithMock(dbapi, '_convert_model_list')
        dbapi._convert_model_list(objects, dbapi._exists_extra_values)
        self.mox.ReplayAll()
        resp = dbapi.list_usage_exists(fake_request)
        self.assertEqual(resp.status_code, 200)
        self.mox.VerifyAll()

    def test_list_usage_exists_with_received_max(self):
        fake_request = self.mox.CreateMockAnything()
        date = str(datetime.datetime.utcnow())
        fake_request.GET = {'received_max': date}
        unix_date = stacktach_utils.str_time_to_unix(date)
        custom_filters = {'received_max': {'raw__when__lte': unix_date}}
        objects = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        dbapi.get_db_objects(models.InstanceExists, fake_request, 'id',
                             custom_filters=custom_filters).AndReturn(objects)
        self.mox.StubOutWithMock(dbapi, '_convert_model_list')
        dbapi._convert_model_list(objects, dbapi._exists_extra_values)
        self.mox.ReplayAll()

        resp = dbapi.list_usage_exists(fake_request)
        self.assertEqual(resp.status_code, 200)
        self.mox.VerifyAll()

    def test_list_usage_exists_with_bad_received_min(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'received_min': 'obviouslybaddate'}
        self.mox.ReplayAll()
        resp = dbapi.list_usage_exists(fake_request)
        self.assertEqual(resp.status_code, 400)
        self.mox.VerifyAll()

    def test_list_usage_exists_with_bad_received_max(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'received_max': 'obviouslybaddate'}
        self.mox.ReplayAll()
        resp = dbapi.list_usage_exists(fake_request)
        self.assertEqual(resp.status_code, 400)
        self.mox.VerifyAll()

    def test_update_tenant_info(self):
        TEST_TENANT='test'

        models.TenantInfo.objects = self.mox.CreateMockAnything()
        models.TenantType.objects = self.mox.CreateMockAnything()

        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        body_dict = dict(tenant=TEST_TENANT,
                         name='test name',
                         types=dict(test_type='thingy'))
        body = json.dumps(body_dict)
        fake_request.body = body

        info = self.mox.CreateMockAnything()
        info_result = self.mox.CreateMockAnything()
        models.TenantInfo.objects.select_for_update().AndReturn(info_result)
        info_result.get(tenant=TEST_TENANT).AndReturn(info)
        info.save()

        ttype = self.mox.CreateMockAnything()
        models.TenantType.objects.get(name='test_type', value='thingy').AndReturn(ttype)
        ttype.__hash__().AndReturn(hash('test_type'))
        info.save()

        self.mox.ReplayAll()

        dbapi.update_tenant_info(fake_request, TEST_TENANT)

        self.assertEqual(info.name, 'test name')
        self.assertEqual(info.types, [ttype])
        self.mox.VerifyAll()

    def test_batch_update_tenant_info(self):
        TEST_DATE='test date time'

        mock_t1 = self.mox.CreateMock(models.TenantInfo)
        mock_t1.id = 1
        mock_t1.tenant = 'test_old'
        mock_t1.name = 'test old name'
        mock_t1.types = self.mox.CreateMockAnything()
        mock_t1.types.all().AndReturn([])
        mock_t1.last_updated = TEST_DATE

        mock_t2 = self.mox.CreateMock(models.TenantInfo)
        mock_t2.id = 2
        mock_t2.tenant = 'test_new'
        mock_t2.name = 'test new name'
        mock_t2.last_updated = TEST_DATE
        mock_t2.types = self.mox.CreateMockAnything()
        mock_t2.types.all().AndReturn([])
        TEST_OBJECTS = [mock_t1, mock_t2]

        mock_tt1 = self.mox.CreateMock(models.TenantType)
        mock_tt1.id = 1
        mock_tt1.name = 'test_type'
        mock_tt1.value = 'thingy'

        mock_tt2 = self.mox.CreateMock(models.TenantType)
        mock_tt2.id = 2
        mock_tt2.name = 'test_type'
        mock_tt2.value = 'whatzit'
        TEST_TYPES = [mock_tt1, mock_tt2]

        models.TenantInfo.objects = self.mox.CreateMockAnything()
        models.TenantType.objects = self.mox.CreateMockAnything()
        TypeXref = models.TenantInfo.types.through
        TypeXref.objects = self.mox.CreateMockAnything()

        self.mox.StubOutWithMock(dbapi, 'datetime')
        dbapi.datetime.utcnow().AndReturn(TEST_DATE)

        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        body_dict = dict(tenants=[dict(tenant='test_old',
                                       name='test old name',
                                       types=dict(test_type='thingy')),
                                  dict(tenant='test_new',
                                       name='test new name',
                                       types=dict(test_type='whatzit'))])
        body = json.dumps(body_dict)
        fake_request.body = body

        info_values = self.mox.CreateMockAnything()
        models.TenantInfo.objects.filter(tenant__in=mox.SameElementsAs(['test_old', 'test_new'])).AndReturn(info_values)
        info_values.values('tenant').AndReturn([dict(tenant='test_old')])
        models.TenantInfo.objects.bulk_create(mox.And(
            Length(1), mox.IsA(list), mox.In(mox.And(
                     mox.IsA(models.TenantInfo),
                     mox.ContainsAttributeValue('tenant','test_new'),
                     mox.ContainsAttributeValue('name', 'test new name'),
                     mox.ContainsAttributeValue('last_updated', TEST_DATE)
                     ))))

        fake_tenants = self.mox.CreateMockAnything()
        models.TenantInfo.objects.filter(tenant__in=mox.SameElementsAs(['test_old', 'test_new']))\
                .AndReturn(fake_tenants)
        fake_tenants.update(last_updated=TEST_DATE)
        fake_tenants.__iter__().AndReturn(iter(TEST_OBJECTS))

        models.TenantType.objects.all().AndReturn(TEST_TYPES)

        mock_query = self.mox.CreateMockAnything()
        TypeXref.objects.filter(tenantinfo_id__in=[]).AndReturn(mock_query)
        mock_query.delete()

        TypeXref.objects.bulk_create(mox.And(
            Length(2), mox.IsA(list),
            mox.In(mox.And(
                     mox.IsA(TypeXref),
                     mox.ContainsAttributeValue('tenantinfo_id', 1),
                     mox.ContainsAttributeValue('tenanttype_id', 1))),
            mox.In(mox.And(
                     mox.IsA(TypeXref),
                     mox.ContainsAttributeValue('tenantinfo_id', 2),
                     mox.ContainsAttributeValue('tenanttype_id', 2))),
            ))

        self.mox.ReplayAll()
        dbapi.batch_update_tenant_info(fake_request)
        self.mox.VerifyAll()

    def test_send_status(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        body_dict = {'send_status': 200}
        body = json.dumps(body_dict)
        fake_request.body = body
        exists = self.mox.CreateMockAnything()
        result = self.mox.CreateMockAnything()
        models.InstanceExists.objects.select_for_update().AndReturn(result)
        result.get(message_id=MESSAGE_ID_1).AndReturn(exists)
        exists.save()
        self.mox.ReplayAll()

        dbapi.exists_send_status(fake_request, MESSAGE_ID_1)

        self.assertEqual(exists.send_status, 200)
        self.mox.VerifyAll()

    def test_send_status_accepts_post(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'POST'
        body_dict = {'send_status': 200}
        body = json.dumps(body_dict)
        fake_request.body = body
        exists = self.mox.CreateMockAnything()
        result = self.mox.CreateMockAnything()
        models.InstanceExists.objects.select_for_update().AndReturn(result)
        result.get(message_id=MESSAGE_ID_1).AndReturn(exists)
        exists.save()
        self.mox.ReplayAll()

        dbapi.exists_send_status(fake_request, MESSAGE_ID_1)

        self.assertEqual(exists.send_status, 200)
        self.mox.VerifyAll()

    def test_send_status_not_found(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        body_dict = {'send_status': 200}
        body = json.dumps(body_dict)
        fake_request.body = body
        result = self.mox.CreateMockAnything()
        models.InstanceExists.objects.select_for_update().AndReturn(result)
        exception = models.InstanceExists.DoesNotExist()
        result.get(message_id=MESSAGE_ID_1).AndRaise(exception)
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, MESSAGE_ID_1)

        self.assertEqual(resp.status_code, 404)
        body = json.loads(resp.content)
        self.assertEqual(body.get("status"), 404)
        msg = "Could not find Exists record with message_id = '%s'"
        msg = msg % MESSAGE_ID_1
        self.assertEqual(body.get("message"), msg)
        self.mox.VerifyAll()

    def test_send_status_multiple_results(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        body_dict = {'send_status': 200}
        body = json.dumps(body_dict)
        fake_request.body = body
        result = self.mox.CreateMockAnything()
        models.InstanceExists.objects.select_for_update().AndReturn(result)
        exception = models.InstanceExists.MultipleObjectsReturned()
        result.get(message_id=MESSAGE_ID_1).AndRaise(exception)
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, MESSAGE_ID_1)

        self.assertEqual(resp.status_code, 500)
        body = json.loads(resp.content)
        self.assertEqual(body.get("status"), 500)
        msg = "Multiple Exists records with message_id = '%s'"
        msg = msg % MESSAGE_ID_1
        self.assertEqual(body.get("message"), msg)
        self.mox.VerifyAll()

    def test_send_status_wrong_method(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.body = None
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, MESSAGE_ID_1)
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertEqual(body.get("status"), 400)
        self.assertEqual(body.get("message"), "Invalid method")
        self.mox.VerifyAll()

    def test_send_status_no_body(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        fake_request.body = None
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, MESSAGE_ID_1)
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertEqual(body.get("status"), 400)
        self.assertEqual(body.get("message"), "Request body required")
        self.mox.VerifyAll()

    def test_send_status_bad_body(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        body_dict = {'bad': 'body'}
        body = json.dumps(body_dict)
        fake_request.body = body
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, MESSAGE_ID_1)
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertEqual(body.get("status"), 400)
        msg = "'send_status' missing from request body"
        self.assertEqual(body.get("message"), msg)
        self.mox.VerifyAll()

    def test_send_status_batch_accepts_post_when_version_is_not_given(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'POST'
        messages = {
            MESSAGE_ID_1: 201, MESSAGE_ID_2: 400
        }
        body_dict = {'messages': messages}
        body = json.dumps(body_dict)
        fake_request.body = body
        self.mox.StubOutWithMock(transaction, 'commit_on_success')
        trans_obj = self.mox.CreateMockAnything()
        transaction.commit_on_success().AndReturn(trans_obj)
        trans_obj.__enter__()
        for uuid, code in messages.items():
            results = self.mox.CreateMockAnything()
            models.InstanceExists.objects.select_for_update().AndReturn(results)
            exists = self.mox.CreateMockAnything()
            results.get(message_id=uuid).AndReturn(exists)
            exists.save()
        trans_obj.__exit__(None, None, None)
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, 'batch')
        self.assertEqual(resp.status_code, 200)
        exists.send_status = 200
        self.mox.VerifyAll()

    def test_send_status_batch_accepts_post_for_nova_and_glance_when_version_is_1(
            self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'POST'
        fake_request.GET = {'service': 'glance'}
        messages = {
            'nova': {MESSAGE_ID_3: 201},
            'glance': {MESSAGE_ID_1: 201, MESSAGE_ID_2: 201}
        }
        body_dict = {'version': 1, 'messages': messages}
        body = json.dumps(body_dict)
        fake_request.body = body
        self.mox.StubOutWithMock(transaction, 'commit_on_success')
        trans_obj = self.mox.CreateMockAnything()
        transaction.commit_on_success().AndReturn(trans_obj)
        trans_obj.__enter__()
        results1 = self.mox.CreateMockAnything()
        models.InstanceExists.objects.select_for_update().AndReturn(results1)
        exists1 = self.mox.CreateMockAnything()
        results1.get(message_id=MESSAGE_ID_3).AndReturn(exists1)
        exists1.save()
        trans_obj.__exit__(None, None, None)

        trans_obj = self.mox.CreateMockAnything()
        transaction.commit_on_success().AndReturn(trans_obj)
        trans_obj.__enter__()

        for uuid, code in messages['glance'].items():
            query = self.mox.CreateMockAnything()
            models.ImageExists.objects.select_for_update().AndReturn(query)
            existsA = self.mox.CreateMockAnything()
            existsB = self.mox.CreateMockAnything()
            query.filter(message_id=uuid).AndReturn([existsA, existsB])
            existsA.save()
            existsB.save()

        trans_obj.__exit__(None, None, None)
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, 'batch')
        self.assertEqual(resp.status_code, 200)
        self.mox.VerifyAll()


    def test_send_status_batch_accepts_post_when_version_is_0(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'POST'
        messages = {MESSAGE_ID_1: 201, MESSAGE_ID_2: 201}
        body_dict = {'version': 0, 'messages': messages}
        body = json.dumps(body_dict)
        fake_request.body = body
        self.mox.StubOutWithMock(transaction, 'commit_on_success')
        trans_obj = self.mox.CreateMockAnything()
        transaction.commit_on_success().AndReturn(trans_obj)
        trans_obj.__enter__()
        for uuid, code in messages.items():
            results = self.mox.CreateMockAnything()
            models.InstanceExists.objects.select_for_update().AndReturn(results)
            exists = self.mox.CreateMockAnything()
            results.get(message_id=uuid).AndReturn(exists)
            exists.save()
        trans_obj.__exit__(None, None, None)
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, 'batch')
        self.assertEqual(resp.status_code, 200)
        self.mox.VerifyAll()

    def test_send_status_batch_accepts_post_for_nova_and_glance_when_version_is_2(
            self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'POST'
        fake_request.GET = {'service': 'glance'}
        messages = {
            'nova': {MESSAGE_ID_3: {'status': 201,
                                    'event_id':
                                        '95347e4d-4737-4438-b774-6a9219d78d2a'},
                     MESSAGE_ID_4: {'status': 201,
                                    'event_id':
                                        '895347e4d-4737-4438-b774-6a9219d78d2a'}
            },
            'glance': {MESSAGE_ID_1: {'status': 201,
                                      'event_id':
                                          '95347e4d-4737-4438-b774-6a9219d78d2a'},
                       MESSAGE_ID_2: {'status': 201,
                                      'event_id':
                                          '895347e4d-4737-4438-b774-6a9219d78d2a'}
            }
        }
        body_dict = {'version': 2, 'messages': messages}
        body = json.dumps(body_dict)
        fake_request.body = body
        self.mox.StubOutWithMock(transaction, 'commit_on_success')

        trans_obj = self.mox.CreateMockAnything()
        transaction.commit_on_success().AndReturn(trans_obj)
        trans_obj.__enter__()
        for uuid, code in messages['nova'].items():
            results = self.mox.CreateMockAnything()
            models.InstanceExists.objects.select_for_update().AndReturn(results)
            exists = self.mox.CreateMockAnything()
            results.get(message_id=uuid).AndReturn(exists)
            exists.save()
        trans_obj.__exit__(None, None, None)

        trans_obj = self.mox.CreateMockAnything()
        transaction.commit_on_success().AndReturn(trans_obj)
        trans_obj.__enter__()
        for uuid, code in messages['glance'].items():
            results = self.mox.CreateMockAnything()
            models.ImageExists.objects.select_for_update().AndReturn(results)
            existsA = self.mox.CreateMockAnything()
            existsB = self.mox.CreateMockAnything()
            results.filter(message_id=uuid).AndReturn([existsA, existsB])
            existsA.save()
            existsB.save()
        trans_obj.__exit__(None, None, None)
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, 'batch')
        self.assertEqual(resp.status_code, 200)
        self.mox.VerifyAll()

    def test_send_status_batch_not_found(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        messages = {
            MESSAGE_ID_1: '201',
        }
        body_dict = {'messages': messages}
        body = json.dumps(body_dict)
        fake_request.body = body
        self.mox.StubOutWithMock(transaction, 'commit_on_success')
        trans_obj = self.mox.CreateMockAnything()
        transaction.commit_on_success().AndReturn(trans_obj)
        trans_obj.__enter__()
        results = self.mox.CreateMockAnything()
        models.InstanceExists.objects.select_for_update().AndReturn(results)
        exception = models.InstanceExists.DoesNotExist()
        results.get(message_id=MESSAGE_ID_1).AndRaise(exception)
        trans_obj.__exit__(dbapi.NotFoundException().__class__,
                           mox.IgnoreArg(),
                           mox.IgnoreArg())
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, 'batch')
        self.assertEqual(resp.status_code, 404)
        body = json.loads(resp.content)
        self.assertEqual(body.get("status"), 404)
        msg = "Could not find Exists record with message_id = '%s' for nova"
        msg = msg % MESSAGE_ID_1
        self.assertEqual(body.get("message"), msg)
        self.mox.VerifyAll()

    def test_send_status_batch_multiple_results(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        messages = {
            MESSAGE_ID_1: 201,
        }
        body_dict = {'messages': messages}
        body = json.dumps(body_dict)
        fake_request.body = body
        self.mox.StubOutWithMock(transaction, 'commit_on_success')
        trans_obj = self.mox.CreateMockAnything()
        transaction.commit_on_success().AndReturn(trans_obj)
        trans_obj.__enter__()
        results = self.mox.CreateMockAnything()
        models.InstanceExists.objects.select_for_update().AndReturn(results)
        exception = models.InstanceExists.MultipleObjectsReturned()
        results.get(message_id=MESSAGE_ID_1).AndRaise(exception)
        trans_obj.__exit__(dbapi.APIException().__class__,
                           mox.IgnoreArg(),
                           mox.IgnoreArg())
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, 'batch')
        self.assertEqual(resp.status_code, 500)
        body = json.loads(resp.content)
        self.assertEqual(body.get("status"), 500)
        msg = "Multiple Exists records with message_id = '%s' for nova"
        msg = msg % MESSAGE_ID_1
        self.assertEqual(body.get("message"), msg)
        self.mox.VerifyAll()

    def test_send_status_batch_wrong_method(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, 'batch')
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertEqual(body.get('status'), 400)
        self.assertEqual(body.get('message'), "Invalid method")
        self.mox.VerifyAll()

    def test_send_status_batch_no_body(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'service': 'nova'}
        fake_request.method = 'PUT'
        fake_request.body = None
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, 'batch')
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertEqual(body.get('status'), 400)
        self.assertEqual(body.get('message'), "Request body required")
        self.mox.VerifyAll()

    def test_send_status_batch_empty_body(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        fake_request.body = ''
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, 'batch')
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertEqual(body.get('status'), 400)
        self.assertEqual(body.get('message'), "Request body required")
        self.mox.VerifyAll()

    def test_send_status_batch_bad_body(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'PUT'
        fake_request.GET = {'service': 'nova'}
        body_dict = {'bad': 'body'}
        fake_request.body = json.dumps(body_dict)
        self.mox.ReplayAll()

        resp = dbapi.exists_send_status(fake_request, 'batch')
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertEqual(body.get('status'), 400)
        msg = "'messages' missing from request body"
        self.assertEqual(body.get('message'), msg)
        self.mox.VerifyAll()

    def test_list_usage_launches_without_service(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        mock_objects = self.mox.CreateMockAnything()
        launches = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_convert_model_list')
        dbapi._convert_model_list(mock_objects).AndReturn(launches)
        dbapi.get_db_objects(models.InstanceUsage, fake_request,
                             'launched_at').AndReturn(mock_objects)
        self.mox.ReplayAll()

        resp = dbapi.list_usage_launches(fake_request)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'launches': launches})
        self.mox.VerifyAll()

    def test_list_usage_launches_for_glance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        mock_objects = self.mox.CreateMockAnything()
        launches = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_convert_model_list')
        dbapi._convert_model_list(mock_objects).AndReturn(launches)
        dbapi.get_db_objects(models.ImageUsage, fake_request,
                             'created_at').AndReturn(mock_objects)
        self.mox.ReplayAll()

        resp = dbapi.list_usage_images(fake_request)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'images': launches})
        self.mox.VerifyAll()

    def test_list_usage_launches_for_nova(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        mock_objects = self.mox.CreateMockAnything()
        launches = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_convert_model_list')
        dbapi._convert_model_list(mock_objects).AndReturn(launches)
        dbapi.get_db_objects(models.InstanceUsage, fake_request,
                             'launched_at').AndReturn(mock_objects)
        self.mox.ReplayAll()

        resp = dbapi.list_usage_launches(fake_request)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'launches': launches})
        self.mox.VerifyAll()

    def test_get_usage_launch_with_no_service(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        launch = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_get_model_by_id')
        dbapi._get_model_by_id(models.InstanceUsage, 1).AndReturn(launch)
        self.mox.ReplayAll()

        resp = dbapi.get_usage_launch(fake_request, 1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'launch': {'a': 1}})
        self.mox.VerifyAll()

    def test_get_usage_launch_for_nova(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        launch = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_get_model_by_id')
        dbapi._get_model_by_id(models.InstanceUsage, 1).AndReturn(launch)
        self.mox.ReplayAll()

        resp = dbapi.get_usage_launch(fake_request, 1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'launch': {'a': 1}})
        self.mox.VerifyAll()

    def test_get_usage_launch_for_glance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        launch = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_get_model_by_id')
        dbapi._get_model_by_id(models.ImageUsage, 1).AndReturn(launch)
        self.mox.ReplayAll()

        resp = dbapi.get_usage_image(fake_request, 1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'launch': {'a': 1}})
        self.mox.VerifyAll()

    def test_get_usage_delete_for_nova(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        delete = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_get_model_by_id')
        dbapi._get_model_by_id(models.InstanceDeletes, 1).AndReturn(delete)
        self.mox.ReplayAll()

        resp = dbapi.get_usage_delete(fake_request, 1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'delete': {'a': 1}})
        self.mox.VerifyAll()

    def test_get_usage_delete_for_glance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        delete = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_get_model_by_id')
        dbapi._get_model_by_id(models.ImageDeletes, 1).AndReturn(delete)
        self.mox.ReplayAll()

        resp = dbapi.get_usage_delete_glance(fake_request, 1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'delete': {'a': 1}})
        self.mox.VerifyAll()

    def test_list_usage_deletes_with_no_service(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        mock_objects = self.mox.CreateMockAnything()
        deletes = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_convert_model_list')
        dbapi._convert_model_list(mock_objects).AndReturn(deletes)
        dbapi.get_db_objects(models.InstanceDeletes, fake_request,
                             'launched_at').AndReturn(mock_objects)
        self.mox.ReplayAll()

        resp = dbapi.list_usage_deletes(fake_request)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'deletes': deletes})
        self.mox.VerifyAll()

    def test_list_usage_deletes_for_nova(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        mock_objects = self.mox.CreateMockAnything()
        deletes = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_convert_model_list')
        dbapi._convert_model_list(mock_objects).AndReturn(deletes)
        dbapi.get_db_objects(models.InstanceDeletes, fake_request,
                             'launched_at').AndReturn(mock_objects)
        self.mox.ReplayAll()

        resp = dbapi.list_usage_deletes(fake_request)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'deletes': deletes})
        self.mox.VerifyAll()

    def test_list_usage_deletes_for_glance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        mock_objects = self.mox.CreateMockAnything()
        deletes = {'a': 1}
        self.mox.StubOutWithMock(dbapi, '_convert_model_list')
        dbapi._convert_model_list(mock_objects).AndReturn(deletes)
        dbapi.get_db_objects(models.ImageDeletes, fake_request,
                             'deleted_at').AndReturn(mock_objects)
        self.mox.ReplayAll()

        resp = dbapi.list_usage_deletes_glance(fake_request)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'deletes': deletes})
        self.mox.VerifyAll()

    def test_get_usage_exist_stats_nova(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        query = self.mox.CreateMockAnything()
        models.InstanceExists.objects.filter().AndReturn(query)
        query.values('status', 'send_status').AndReturn(query)
        result = [
            {'status': 'verified', 'send_status': 201L, 'event_count': 2},
            {'status': 'failed', 'send_status': 0L, 'event_count': 1}
        ]
        query.annotate(event_count=mox.IsA(Count)).AndReturn(result)
        self.mox.ReplayAll()
        response = dbapi.get_usage_exist_stats(fake_request)
        self.assertEqual(response.status_code, 200)
        expected_response = json.dumps({'stats': result})
        self.assertEqual(expected_response, response.content)
        self.mox.VerifyAll()

    def test_get_usage_exist_stats_nova_received_min(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        now = datetime.datetime.utcnow()
        fake_request.GET = {'received_min': str(now)}
        query = self.mox.CreateMockAnything()
        filters = {'raw__when__gte': utils.decimal_utc(now)}
        models.InstanceExists.objects.filter(**filters).AndReturn(query)
        query.values('status', 'send_status').AndReturn(query)
        result = [
            {'status': 'verified', 'send_status': 201L, 'event_count': 2},
            {'status': 'failed', 'send_status': 0L, 'event_count': 1}
        ]
        query.annotate(event_count=mox.IsA(Count)).AndReturn(result)
        self.mox.ReplayAll()
        response = dbapi.get_usage_exist_stats(fake_request)
        self.assertEqual(response.status_code, 200)
        expected_response = json.dumps({'stats': result})
        self.assertEqual(expected_response, response.content)
        self.mox.VerifyAll()

    def test_get_usage_exist_stats_nova_received_max(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        now = datetime.datetime.utcnow()
        fake_request.GET = {'received_max': str(now)}
        query = self.mox.CreateMockAnything()
        filters = {'raw__when__lte': utils.decimal_utc(now)}
        models.InstanceExists.objects.filter(**filters).AndReturn(query)
        query.values('status', 'send_status').AndReturn(query)
        result = [
            {'status': 'verified', 'send_status': 201L, 'event_count': 2},
            {'status': 'failed', 'send_status': 0L, 'event_count': 1}
        ]
        query.annotate(event_count=mox.IsA(Count)).AndReturn(result)
        self.mox.ReplayAll()
        response = dbapi.get_usage_exist_stats(fake_request)
        self.assertEqual(response.status_code, 200)
        expected_response = json.dumps({'stats': result})
        self.assertEqual(expected_response, response.content)
        self.mox.VerifyAll()

    def test_get_usage_exist_stats_nova_class_field_filter(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        now = datetime.datetime.utcnow()
        fake_request.GET = {'audit_period_ending_min': str(now)}
        query = self.mox.CreateMockAnything()
        models.InstanceExists._meta.get_field_by_name('audit_period_ending')
        filters = {'audit_period_ending__gte': utils.decimal_utc(now)}
        models.InstanceExists.objects.filter(**filters).AndReturn(query)
        query.values('status', 'send_status').AndReturn(query)
        result = [
            {'status': 'verified', 'send_status': 201L, 'event_count': 2},
            {'status': 'failed', 'send_status': 0L, 'event_count': 1}
        ]
        query.annotate(event_count=mox.IsA(Count)).AndReturn(result)
        self.mox.ReplayAll()
        response = dbapi.get_usage_exist_stats(fake_request)
        self.assertEqual(response.status_code, 200)
        expected_response = json.dumps({'stats': result})
        self.assertEqual(expected_response, response.content)
        self.mox.VerifyAll()

    def test_get_usage_exist_stats_glance(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {}
        query = self.mox.CreateMockAnything()
        models.ImageExists.objects.filter().AndReturn(query)
        query.values('status', 'send_status').AndReturn(query)
        result = [
            {'status': 'verified', 'send_status': 201L, 'event_count': 2},
            {'status': 'failed', 'send_status': 0L, 'event_count': 1}
        ]
        query.annotate(event_count=mox.IsA(Count)).AndReturn(result)
        self.mox.ReplayAll()
        response = dbapi.get_usage_exist_stats_glance(fake_request)
        self.assertEqual(response.status_code, 200)
        expected_response = json.dumps({'stats': result})
        self.assertEqual(expected_response, response.content)
        self.mox.VerifyAll()

    def test_get_usage_exist_stats_glance_received_min(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        now = datetime.datetime.utcnow()
        fake_request.GET = {'received_min': str(now)}
        query = self.mox.CreateMockAnything()
        filters = {'raw__when__gte': utils.decimal_utc(now)}
        models.ImageExists.objects.filter(**filters).AndReturn(query)
        query.values('status', 'send_status').AndReturn(query)
        result = [
            {'status': 'verified', 'send_status': 201L, 'event_count': 2},
            {'status': 'failed', 'send_status': 0L, 'event_count': 1}
        ]
        query.annotate(event_count=mox.IsA(Count)).AndReturn(result)
        self.mox.ReplayAll()
        response = dbapi.get_usage_exist_stats_glance(fake_request)
        self.assertEqual(response.status_code, 200)
        expected_response = json.dumps({'stats': result})
        self.assertEqual(expected_response, response.content)
        self.mox.VerifyAll()

    def test_get_usage_exist_stats_glance_received_max(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        now = datetime.datetime.utcnow()
        fake_request.GET = {'received_max': str(now)}
        query = self.mox.CreateMockAnything()
        filters = {'raw__when__lte': utils.decimal_utc(now)}
        models.ImageExists.objects.filter(**filters).AndReturn(query)
        query.values('status', 'send_status').AndReturn(query)
        result = [
            {'status': 'verified', 'send_status': 201L, 'event_count': 2},
            {'status': 'failed', 'send_status': 0L, 'event_count': 1}
        ]
        query.annotate(event_count=mox.IsA(Count)).AndReturn(result)
        self.mox.ReplayAll()
        response = dbapi.get_usage_exist_stats_glance(fake_request)
        self.assertEqual(response.status_code, 200)
        expected_response = json.dumps({'stats': result})
        self.assertEqual(expected_response, response.content)
        self.mox.VerifyAll()

    def test_get_usage_exist_stats_glance_class_field_filter(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        now = datetime.datetime.utcnow()
        fake_request.GET = {'audit_period_ending_min': str(now)}
        query = self.mox.CreateMockAnything()
        models.ImageExists._meta.get_field_by_name('audit_period_ending')
        filters = {'audit_period_ending__gte': utils.decimal_utc(now)}
        models.ImageExists.objects.filter(**filters).AndReturn(query)
        query.values('status', 'send_status').AndReturn(query)
        result = [
            {'status': 'verified', 'send_status': 201L, 'event_count': 2},
            {'status': 'failed', 'send_status': 0L, 'event_count': 1}
        ]
        query.annotate(event_count=mox.IsA(Count)).AndReturn(result)
        self.mox.ReplayAll()
        response = dbapi.get_usage_exist_stats_glance(fake_request)
        self.assertEqual(response.status_code, 200)
        expected_response = json.dumps({'stats': result})
        self.assertEqual(expected_response, response.content)
        self.mox.VerifyAll()

    def test_get_event_stats(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {'service': "nova"}
        mock_query = self.mox.CreateMockAnything()
        models.RawData.objects.values('event').AndReturn(mock_query)
        events = [
            {'event': 'compute.instance.exists.verified', 'event_count': 100},
            {'event': 'compute.instance.exists', 'event_count': 100}
        ]
        mock_query.annotate(event_count=mox.IsA(Count)).AndReturn(events)
        self.mox.ReplayAll()

        response = dbapi.get_event_stats(fake_request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content,
                         json.dumps({'stats': events}))
        self.mox.VerifyAll()

    def test_get_event_stats_date_range(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        start = "2014-02-26 00:00:00"
        end = "2014-02-27 00:00:00"
        fake_request.GET = {'when_min': start,
                            'when_max': end,
                            'service': "nova"}
        mock_query = self.mox.CreateMockAnything()
        filters = {
            'when__gte': stacktach_utils.str_time_to_unix(start),
            'when__lte': stacktach_utils.str_time_to_unix(end)
        }
        models.RawData.objects.filter(**filters).AndReturn(mock_query)
        mock_query.values('event').AndReturn(mock_query)
        events = [
            {'event': 'compute.instance.exists.verified', 'event_count': 100},
            {'event': 'compute.instance.exists', 'event_count': 100}
        ]
        mock_query.annotate(event_count=mox.IsA(Count)).AndReturn(events)
        self.mox.ReplayAll()

        response = dbapi.get_event_stats(fake_request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content,
                         json.dumps({'stats': events}))
        self.mox.VerifyAll()

    def test_get_verified_count(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {'service': "nova",
                            'event': 'compute.instance.exists.verified'}
        mock_query = self.mox.CreateMockAnything()
        models.RawData.objects.values('event').AndReturn(mock_query)
        events = [
            {'event': 'compute.instance.exists.verified', 'event_count': 100},
            {'event': 'compute.instance.exists', 'event_count': 100}
        ]
        mock_query.annotate(event_count=mox.IsA(Count)).AndReturn(events)
        self.mox.ReplayAll()

        response = dbapi.get_event_stats(fake_request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content,
                         json.dumps({'stats': [events[0]]}))
        self.mox.VerifyAll()

    def test_get_verified_count_default(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {'service': "nova",
                            'event': 'compute.instance.exists.verified'}
        mock_query = self.mox.CreateMockAnything()
        models.RawData.objects.values('event').AndReturn(mock_query)
        events = [
            {'event': 'compute.instance.create.start', 'event_count': 100},
            {'event': 'compute.instance.exists', 'event_count': 100}
        ]
        mock_query.annotate(event_count=mox.IsA(Count)).AndReturn(events)
        self.mox.ReplayAll()

        response = dbapi.get_event_stats(fake_request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content,
                         json.dumps({'stats': [{'event': 'compute.instance.exists.verified', 'event_count': 0}]}))
        self.mox.VerifyAll()

    def test_get_verified_count_only_one_range_param_returns_400(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {'when_min': "2014-020-26",
                            'service': "nova"}

        self.mox.ReplayAll()

        response = dbapi.get_event_stats(fake_request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['message'],
                         "When providing date range filters, "
                         "a min and max are required.")
        self.mox.VerifyAll()

    def test_get_verified_count_only_large_date_range_returns_400(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {'when_min': "2014-2-26 00:00:00",
                            'when_max': "2014-3-5 00:00:01",  # > 7 days later
                            'service': "nova"}

        self.mox.ReplayAll()

        response = dbapi.get_event_stats(fake_request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['message'],
                         "Date ranges may be no larger than 604800 seconds")
        self.mox.VerifyAll()

    def test_get_verified_count_wrong_date_format_returns_400(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {'when_min': "2014-020-26",
                            'when_max': "2014-020-26",
                            'service': "nova"}

        self.mox.ReplayAll()

        response = dbapi.get_event_stats(fake_request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['message'],
                         "Invalid format for date"
                         " (Correct format should be %Y-%m-%d %H:%M:%S)")
        self.mox.VerifyAll()

    def test_get_verified_count_wrong_service_returns_400(self):
        fake_request = self.mox.CreateMockAnything()
        fake_request.method = 'GET'
        fake_request.GET = {'when_min': "2014-02-26 00:00:00",
                            "when_max": "2014-02-27 00:00:00",
                            'service': "qonos"}

        self.mox.ReplayAll()

        response = dbapi.get_event_stats(fake_request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['message'],
                         "Invalid service")
        self.mox.VerifyAll()


class StacktachRepairScenarioApi(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_change_nova_exists_status_for_all_exists(self):
        request = self.mox.CreateMockAnything()
        request.POST = self.mox.CreateMockAnything()
        message_ids = ["04fd94b5-64dd-4559-83b7-981d9d4f7a5a",
                       "14fd94b5-64dd-4559-83b7-981d9d4f7a5a",
                       "24fd94b5-64dd-4559-83b7-981d9d4f7a5a"]
        request.POST._iterlists().AndReturn([('service', ['nova']),
                                             ('message_ids', message_ids)])
        self.mox.StubOutWithMock(models.InstanceExists,
                                 'mark_exists_as_sent_unverified')
        models.InstanceExists.mark_exists_as_sent_unverified(message_ids).\
            AndReturn([[], []])
        self.mox.ReplayAll()

        response = dbapi.repair_stacktach_down(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['exists_not_pending'], [])
        self.assertEqual(response_data['absent_exists'], [])

        self.mox.VerifyAll()

    def test_change_glance_exists_status_for_all_exists(self):
        request = self.mox.CreateMockAnything()
        request.POST = self.mox.CreateMockAnything()
        message_ids = ['04fd94b5-64dd-4559-83b7-981d9d4f7a5a',
                       '14fd94b5-64dd-4559-83b7-981d9d4f7a5a',
                       '24fd94b5-64dd-4559-83b7-981d9d4f7a5a']
        request.POST._iterlists().AndReturn([('service', ['glance']),
                                             ('message_ids', message_ids)])
        self.mox.StubOutWithMock(models.ImageExists,
                                 'mark_exists_as_sent_unverified')
        models.ImageExists.mark_exists_as_sent_unverified(message_ids).\
            AndReturn([[], []])
        self.mox.ReplayAll()

        response = dbapi.repair_stacktach_down(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['exists_not_pending'], [])
        self.assertEqual(response_data['absent_exists'], [])

        self.mox.VerifyAll()
