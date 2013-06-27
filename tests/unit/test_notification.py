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

from decimal import Decimal
import unittest
from stacktach.notification import Notification
from tests.unit.utils import REQUEST_ID_1, TENANT_ID_1, INSTANCE_ID_1


class NotificationTestCase(unittest.TestCase):

    def test_rawdata_kwargs(self):
        message = {
            'event_type': 'compute.instance.create.start',
            'publisher_id': 'compute.cpu1-n01.example.com',
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            'timestamp': '2013-06-12 06:30:52.790476',
            'payload': {
                'instance_id': INSTANCE_ID_1,
                'state': 'active',
                'old_state': 'building',
                'old_task_state': 'build',
                "new_task_state": 'rebuild_spawning',
                'image_meta': {
                    'image_type': 'base',
                    'org.openstack__1__architecture': 'x64',
                    'org.openstack__1__os_distro': 'com.microsoft.server',
                    'org.openstack__1__os_version': '2008.2',
                    'com.rackspace__1__options': '36'
                }
            }
        }
        kwargs = Notification(message).rawdata_kwargs('1', 'monitor.info', 'json')

        self.assertEquals(kwargs['host'], 'cpu1-n01.example.com')
        self.assertEquals(kwargs['deployment'], '1')
        self.assertEquals(kwargs['routing_key'], 'monitor.info')
        self.assertEquals(kwargs['tenant'], TENANT_ID_1)
        self.assertEquals(kwargs['json'], 'json')
        self.assertEquals(kwargs['state'], 'active')
        self.assertEquals(kwargs['old_state'], 'building')
        self.assertEquals(kwargs['old_task'], 'build')
        self.assertEquals(kwargs['task'], 'rebuild_spawning')
        self.assertEquals(kwargs['image_type'], 1)
        self.assertEquals(kwargs['when'], Decimal('1371018652.790476'))
        self.assertEquals(kwargs['publisher'], 'compute.cpu1-n01.example.com')
        self.assertEquals(kwargs['event'], 'compute.instance.create.start')
        self.assertEquals(kwargs['request_id'], REQUEST_ID_1)

    def test_rawdata_kwargs_for_message_with_no_host(self):
        message = {
            'event_type': 'compute.instance.create.start',
            'publisher_id': 'compute',
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            'timestamp': '2013-06-12 06:30:52.790476',
            'payload': {
                'instance_id': INSTANCE_ID_1,
                'state': 'active',
                'old_state': 'building',
                'old_task_state': 'build',
                "new_task_state": 'rebuild_spawning',
                'image_meta': {
                    'image_type': 'base',
                    'org.openstack__1__architecture': 'x64',
                    'org.openstack__1__os_distro': 'com.microsoft.server',
                    'org.openstack__1__os_version': '2008.2',
                    'com.rackspace__1__options': '36'
                }
            }
        }
        kwargs = Notification(message).rawdata_kwargs('1', 'monitor.info', 'json')
        self.assertEquals(kwargs['host'], None)

        self.assertEquals(kwargs['deployment'], '1')
        self.assertEquals(kwargs['routing_key'], 'monitor.info')
        self.assertEquals(kwargs['tenant'], TENANT_ID_1)
        self.assertEquals(kwargs['json'], 'json')
        self.assertEquals(kwargs['state'], 'active')
        self.assertEquals(kwargs['old_state'], 'building')
        self.assertEquals(kwargs['old_task'], 'build')
        self.assertEquals(kwargs['task'], 'rebuild_spawning')
        self.assertEquals(kwargs['image_type'], 1)
        self.assertEquals(kwargs['when'], Decimal('1371018652.790476'))
        self.assertEquals(kwargs['publisher'], 'compute')
        self.assertEquals(kwargs['event'], 'compute.instance.create.start')
        self.assertEquals(kwargs['request_id'], REQUEST_ID_1)

    def test_rawdata_kwargs_for_message_with_exception(self):
        message = {
            'event_type': 'compute.instance.create.start',
            'publisher_id': 'compute.cpu1-n01.example.com',
            '_context_request_id': REQUEST_ID_1,
            '_context_project_id': TENANT_ID_1,
            'timestamp': '2013-06-12 06:30:52.790476',
            'payload': {
                'exception': {'kwargs':{'uuid': INSTANCE_ID_1}},
                'instance_id': INSTANCE_ID_1,
                'state': 'active',
                'old_state': 'building',
                'old_task_state': 'build',
                "new_task_state": 'rebuild_spawning',
                'image_meta': {
                    'image_type': 'base',
                    'org.openstack__1__architecture': 'x64',
                    'org.openstack__1__os_distro': 'com.microsoft.server',
                    'org.openstack__1__os_version': '2008.2',
                    'com.rackspace__1__options': '36'
                }
            }
        }
        kwargs = Notification(message).rawdata_kwargs('1', 'monitor.info', 'json')

        self.assertEquals(kwargs['host'], 'cpu1-n01.example.com')
        self.assertEquals(kwargs['deployment'], '1')
        self.assertEquals(kwargs['routing_key'], 'monitor.info')
        self.assertEquals(kwargs['tenant'], TENANT_ID_1)
        self.assertEquals(kwargs['json'], 'json')
        self.assertEquals(kwargs['state'], 'active')
        self.assertEquals(kwargs['old_state'], 'building')
        self.assertEquals(kwargs['old_task'], 'build')
        self.assertEquals(kwargs['task'], 'rebuild_spawning')
        self.assertEquals(kwargs['image_type'], 1)
        self.assertEquals(kwargs['when'], Decimal('1371018652.790476'))
        self.assertEquals(kwargs['publisher'], 'compute.cpu1-n01.example.com')
        self.assertEquals(kwargs['event'], 'compute.instance.create.start')
        self.assertEquals(kwargs['request_id'], REQUEST_ID_1)
