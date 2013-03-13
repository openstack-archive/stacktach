# Copyright 2012 - Rackspace Inc.

import datetime
import unittest

from django.db.models import FieldDoesNotExist
import mox

from stacktach import dbapi
from stacktach import models
from stacktach import utils as stacktach_utils
import utils
from utils import INSTANCE_ID_1


class DBAPITestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()

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
        fake_model._meta.get_field_by_name('somebadfield')\
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
        result.order_by('id').AndReturn(result)
        result.__getitem__(slice(None, None, None)).AndReturn(result)
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
        result.__getitem__(slice(None, None, None)).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_limit(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'limit': 1}
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn({})
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.all().AndReturn(result)
        result.order_by('id').AndReturn(result)
        result.__getitem__(slice(None, 1, None)).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_offset(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'offset': 1}
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn({})
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.all().AndReturn(result)
        result.order_by('id').AndReturn(result)
        result.__getitem__(slice(1, None, None)).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id')
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_get_db_objects_offset_and_limit(self):
        fake_model = self.make_fake_model()
        fake_request = self.mox.CreateMockAnything()
        fake_request.GET = {'offset': 2, 'limit': 2}
        self.mox.StubOutWithMock(dbapi, '_get_filter_args')
        dbapi._get_filter_args(fake_model, fake_request,
                               custom_filters=None).AndReturn({})
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        fake_model.objects.all().AndReturn(result)
        result.order_by('id').AndReturn(result)
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
        result.order_by('id').AndReturn(result)
        result.__getitem__(slice(None, None, None)).AndReturn(result)
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
                               custom_filters=custom_filters).AndReturn(filters)
        self.mox.StubOutWithMock(dbapi, '_check_has_field')
        dbapi._check_has_field(fake_model, 'id')
        result = self.mox.CreateMockAnything()
        all_filters = {}
        all_filters.update(filters)
        all_filters.update(custom_filters['raw'])
        fake_model.objects.filter(**all_filters).AndReturn(result)
        result.order_by('id').AndReturn(result)
        result.__getitem__(slice(None, None, None)).AndReturn(result)
        self.mox.ReplayAll()

        query_result = dbapi.get_db_objects(fake_model, fake_request, 'id',
                                            custom_filters=custom_filters)
        self.assertEquals(query_result, result)

        self.mox.VerifyAll()

    def test_list_usage_exists_no_custom_filters(self):
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
        self.mox.StubOutWithMock(dbapi, 'get_db_objects')
        unix_date = stacktach_utils.str_time_to_unix(date)
        custom_filters = {'received_max': {'raw__when__lte': unix_date}}
        objects = self.mox.CreateMockAnything()
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