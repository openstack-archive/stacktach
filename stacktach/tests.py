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
from stacktach.models import RawDataImageMeta
from stacktach.models import GenericRawData
from stacktach.models import GlanceRawData
from stacktach.models import RawData
from stacktach.models import get_model_fields


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


class GlanceRawDataTestCase(TransactionTestCase):
    def test_create_rawdata_should_populate_glance_rawdata(self):
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
        rawdata = GlanceRawData.objects.all().order_by('-id')[0]

        for field in get_model_fields(GlanceRawData):
            if field.name != 'id':
                self.assertEquals(getattr(rawdata, field.name),
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
            'image_type': 1,
            'publisher': 'publisher',
            'event': 'event',
            'service': 'service',
            'host': 'host',
            'instance': '1234-5678-9012-3456',
            'request_id': '1234'}

        db.create_generic_rawdata(**kwargs)
        rawdata = GenericRawData.objects.all()[0]

        for field in get_model_fields(GenericRawData):
            if field.name != 'id':
                self.assertEquals(getattr(rawdata, field.name),
                                  kwargs[field.name])
