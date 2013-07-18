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
from django.test import TransactionTestCase
import db
from stacktach.datetime_to_decimal import dt_to_decimal
from stacktach.models import RawDataImageMeta, ImageUsage, ImageDeletes
from stacktach.models import GenericRawData
from stacktach.models import GlanceRawData
from stacktach.models import RawData
from stacktach.models import get_model_fields
from stacktach import datetime_to_decimal as dt



class RawDataImageMetaDbTestCase(TransactionTestCase):
    def test_create_raw_data_should_populate_rawdata_and_rawdata_imagemeta(self):
        deployment = db.get_or_create_deployment('deployment1')[0]
        kwargs = {
            'deployment': deployment,
            'when': dt_to_decimal(datetime.utcnow()),
            'tenant': '1',
            'json': '{}',
            'routing_key': 'monitor.info',
            'state': 'verifying',
            'old_state': 'pending',
            'old_task': 'building',
            'task': 'saving',
            'image_type': 1,
            'publisher': 'publisher',
            'event': 'compute.instance.exists',
            'service': 'compute',
            'host': 'host',
            'instance': '1234-5678-9012-3456',
            'request_id': '1234',
            'os_architecture': 'x86',
            'os_version': '1',
            'os_distro': 'windows',
            'rax_options': '2'}

        rawdata = db.create_nova_rawdata(**kwargs)

        for field in get_model_fields(RawData):
            if field.name != 'id':
                self.assertEquals(getattr(rawdata, field.name),
                                  kwargs[field.name])

        raw_image_meta = RawDataImageMeta.objects.filter(raw_id=rawdata.id)[0]
        self.assertEquals(raw_image_meta.os_architecture,
                          kwargs['os_architecture'])
        self.assertEquals(raw_image_meta.os_version, kwargs['os_version'])
        self.assertEquals(raw_image_meta.os_distro, kwargs['os_distro'])
        self.assertEquals(raw_image_meta.rax_options, kwargs['rax_options'])


class GlanceTestCase(TransactionTestCase):
    def _create_glance_rawdata(self):
        deployment = db.get_or_create_deployment('deployment1')[0]
        kwargs = {
            'deployment': deployment,
            'when': dt_to_decimal(datetime.utcnow()),
            'owner': '1234567',
            'json': '{}',
            'routing_key': 'glance_monitor.info',
            'image_type': 1,
            'publisher': 'publisher',
            'event': 'event',
            'service': 'service',
            'host': 'host',
            'instance': '1234-5678-9012-3456',
            'request_id': '1234',
            'uuid': '1234-5678-0912-3456',
            'status': 'active',
        }
        db.create_glance_rawdata(**kwargs)
        rawdata = GlanceRawData.objects.all()[0]
        return kwargs, rawdata

    def test_create_rawdata_should_populate_glance_rawdata(self):
        kwargs, rawdata = self._create_glance_rawdata()

        for field in get_model_fields(GlanceRawData):
            if field.name != 'id':
                self.assertEquals(getattr(rawdata, field.name),
                                  kwargs[field.name])

    def test_create_glance_usage_should_populate_image_usage(self):
        _, rawdata = self._create_glance_rawdata()
        kwargs = {
            'uuid': '1',
            'created_at': dt_to_decimal(datetime.utcnow()),
            'owner': '1234567',
            'size': 12345,
            'last_raw': rawdata
        }
        db.create_image_usage(**kwargs)
        usage = ImageUsage.objects.all()[0]

        for field in get_model_fields(ImageUsage):
            if field.name != 'id':
                self.assertEquals(getattr(usage, field.name),
                                  kwargs[field.name])

    def test_create_image_delete_should_populate_image_delete(self):
        _, rawdata = self._create_glance_rawdata()
        kwargs = {
            'uuid': '1',
            'raw': rawdata,
            'deleted_at': dt_to_decimal(datetime.utcnow())
        }
        db.create_image_delete(**kwargs)
        image_delete = ImageDeletes.objects.all()[0]

        for field in get_model_fields(ImageDeletes):
            if field.name != 'id':
                self.assertEquals(getattr(image_delete, field.name),
                                  kwargs[field.name])


class GenericRawDataTestCase(TransactionTestCase):
    def test_create_generic_rawdata_should_populate_generic_rawdata(self):
        deployment = db.get_or_create_deployment('deployment1')[0]
        kwargs = {
            'deployment': deployment,
            'when': dt_to_decimal(datetime.utcnow()),
            'tenant': '1234567',
            'json': '{}',
            'routing_key': 'monitor.info',
            'publisher': 'publisher',
            'event': 'event',
            'service': 'service',
            'host': 'host',
            'instance': '1234-5678-9012-3456',
            'request_id': '1234',
            'message_id': 'message_id'}

        db.create_generic_rawdata(**kwargs)
        rawdata = GenericRawData.objects.all()[0]

        for field in get_model_fields(GenericRawData):
            if field.name != 'id':
                self.assertEquals(getattr(rawdata, field.name),
                                  kwargs[field.name])


class NovaRawDataSearchTestCase(TransactionTestCase):
    def test_search_results_for_nova(self):
        expected_result = [['#', '?', 'When', 'Deployment', 'Event', 'Host',
                            'State', "State'", "Task'"], [1L, ' ',
                            '2013-07-17 10:16:10.717219', 'depl', 'event',
                            'host', 'state', 'old_state', 'old_task']]
        depl = db.get_or_create_deployment('depl')[0]
        when = dt.dt_to_decimal(datetime.utcnow())
        raw = db.create_nova_rawdata(deployment=depl,
                      routing_key='routing_key',
                                      tenant='tenant',
                                      json='json',
                                      when=when,
                                      publisher='publisher',
                                      event='event',
                                      service='nova',
                                      host='host',
                                      instance='instance',
                                      request_id='req-1234',
                                      state='state',
                                      old_state='old_state',
                                      task='task',
                                      old_task='old_task',
                                      os_architecture='arch',
                                      os_distro='distro',
                                      os_version='version',
                                      rax_options=1)

        results = raw.search_results({}, "2013-07-17 10:16:10.717219", ' ')
        self.assertEqual(results,expected_result)

    def test_search_results_for_glance(self):
        expected_result = [['#', '?', 'When', 'Deployment', 'Event', 'Host',
                            'Status'], [1L, ' ',
                            '2013-07-17 10:16:10.717219', 'depl', 'event',
                            'host', 'status']]
        depl = db.get_or_create_deployment('depl')[0]
        when = dt.dt_to_decimal(datetime.utcnow())

        glance_raw = db.create_glance_rawdata(deployment=depl,
                                              routing_key='routing_key',
                                              json='json',
                                              when=when,
                                              publisher='publisher',
                                              event='event',
                                              service='glance',
                                              host='host',
                                              uuid='instance',
                                              request_id='req-1234',
                                              status='status',
                                              image_type=1)

        results = glance_raw.search_results({}, "2013-07-17 10:16:10.717219",
                                                ' ')
        self.assertEqual(results,expected_result)

    def test_search_results_for_generic(self):
        expected_result = [['#', '?', 'When', 'Deployment', 'Event', 'Host',
                            'Instance', 'Request id'], [1L, ' ',
                            '2013-07-17 10:16:10.717219', 'depl', 'event',
                            'host', 'instance', 'req-1234']]
        depl = db.get_or_create_deployment('depl')[0]
        when = dt.dt_to_decimal(datetime.utcnow())

        generic_raw = db.create_generic_rawdata(deployment=depl,
                                              routing_key='routing_key',
                                              json='json',
                                              when=when,
                                              publisher='publisher',
                                              event='event',
                                              service='glance',
                                              host='host',
                                              instance='instance',
                                              request_id='req-1234',
                                              tenant='tenant')

        results = generic_raw.search_results({}, "2013-07-17 10:16:10.717219",
                                                ' ')
        self.assertEqual(results,expected_result)
