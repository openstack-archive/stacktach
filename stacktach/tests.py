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
import db
from stacktach.datetime_to_decimal import dt_to_decimal
from stacktach.models import RawDataImageMeta
from stacktach.models import RawData
from stacktach.models import get_model_fields


class RawDataImageMetaDbTestCase(unittest.TestCase):
    def test_create_raw_data_should_populate_rawdata_and_rawdata_imagemeta(self):
        deployment = db.get_or_create_deployment('deployment1')[0]
        kwargs = {
            'deployment': deployment,
            'when': dt_to_decimal(datetime.utcnow()),
            'tenant': '1', 'json': '{}', 'routing_key': 'monitor.info',
            'state': 'verifying', 'old_state': 'pending',
            'old_task': '', 'task': '', 'image_type': 1,
            'publisher': '', 'event': 'compute.instance.exists',
            'service': '', 'host': '', 'instance': '1234-5678-9012-3456',
            'request_id': '1234', 'os_architecture': 'x86', 'os_version': '1',
            'os_distro': 'windows', 'rax_options': '2'}

        rawdata = db.create_rawdata(**kwargs)

        for field in get_model_fields(RawData):
            if field.name != 'id':
                self.assertEquals(getattr(rawdata, field.name),
                                  kwargs[field.name])

        raw_image_meta = RawDataImageMeta.objects.all()[0]
        self.assertEquals(raw_image_meta.raw, rawdata)
        self.assertEquals(raw_image_meta.os_architecture,
                          kwargs['os_architecture'])
        self.assertEquals(raw_image_meta.os_version, kwargs['os_version'])
        self.assertEquals(raw_image_meta.os_distro, kwargs['os_distro'])
        self.assertEquals(raw_image_meta.rax_options, kwargs['rax_options'])
