# Copyright (c) 2012 - Rackspace Inc.
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
import decimal

TENANT_ID_1 = 'testtenantid1'
TENANT_ID_2 = 'testtenantid2'

from stacktach import datetime_to_decimal as dt

IMAGE_UUID_1 = "12345678-6352-4dbc-8271-96cc54bf14cd"

INSTANCE_ID_1 = "08f685d9-6352-4dbc-8271-96cc54bf14cd"
INSTANCE_ID_2 = "515adf96-41d3-b86d-5467-e584edc61dab"

INSTANCE_FLAVOR_ID_1 = "1"
INSTANCE_FLAVOR_ID_2 = "performance2-120"

INSTANCE_TYPE_ID_1 = "12345"
INSTANCE_TYPE_ID_2 = '54321'

DUMMY_TIME = datetime.datetime.utcnow()
DECIMAL_DUMMY_TIME = dt.dt_to_decimal(DUMMY_TIME)

MESSAGE_ID_1 = "7f28f81b-29a2-43f2-9ba1-ccb3e53ab6c8"
MESSAGE_ID_2 = "4d596126-0f04-4329-865f-7b9a7bd69bcf"
MESSAGE_ID_3 = "4d596126-0f04-4329-865f-797387adf45c"

BANDWIDTH_PUBLIC_OUTBOUND = 1697240969

REQUEST_ID_1 = 'req-611a4d70-9e47-4b27-a95e-27996cc40c06'
REQUEST_ID_2 = 'req-a951dec0-52ee-425d-9f56-d68bd1ad00ac'
REQUEST_ID_3 = 'req-039a33f7-5849-4406-8166-4db8cd085f52'

RAX_OPTIONS_1 = '1'
RAX_OPTIONS_2 = '2'

OS_DISTRO_1 = "linux"
OS_DISTRO_2 = "selinux"

OS_ARCH_1 = "x86"
OS_ARCH_2 = "x64"

OS_VERSION_1 = "1"
OS_VERSION_2 = "2"

LAUNCHED_AT_1 = decimal.Decimal("1.1")
LAUNCHED_AT_2 = decimal.Decimal("2.1")

DELETED_AT_1 = decimal.Decimal("3.1")
DELETED_AT_2 = decimal.Decimal("4.1")

SIZE_1 = 1234
SIZE_2 = 4567

CREATED_AT_1 = decimal.Decimal("10.1")
CREATED_AT_2 = decimal.Decimal("11.1")

TIMESTAMP_1 = "2013-06-20 17:31:57.939614"
SETTLE_TIME = 5
SETTLE_UNITS = "minutes"
TICK_TIME = 10
HOST = '10.0.0.1'
PORT = '5672'
VIRTUAL_HOST = '/'
USERID = 'rabbit'
PASSWORD = 'password'
NOVA_VERIFIER_EVENT_TYPE = 'compute.instance.exists.verified.old'
GLANCE_VERIFIER_EVENT_TYPE = 'image.exists.verified.old'
FLAVOR_FIELD_NAME = 'flavor_field_name'

def decimal_utc(t = datetime.datetime.utcnow()):
    return dt.dt_to_decimal(t)


def create_nova_notif(request_id=None, instance=INSTANCE_ID_1, type_id='1',
                      launched=None, deleted=None, new_type_id=None,
                      message_id=MESSAGE_ID_1, audit_period_beginning=None,
                      audit_period_ending=None, tenant_id=None,
                      rax_options=None, os_architecture=None,
                      os_version=None, os_distro=None):
    notif = ['', {
        'message_id': message_id,
        'payload': {
            'image_meta': {},
            'instance_id': instance,
            'instance_type_id': type_id,
        }
    }]

    notif[1]['_context_request_id'] = request_id
    notif[1]['payload']['launched_at'] = launched
    notif[1]['payload']['deleted_at'] = deleted
    notif[1]['payload']['new_instance_type_id'] = new_type_id
    notif[1]['payload']['audit_period_beginning'] = audit_period_beginning
    notif[1]['payload']['audit_period_ending'] = audit_period_ending
    notif[1]['payload']['tenant_id'] = tenant_id
    notif[1]['payload']['image_meta']['com.rackspace__1__options'] = rax_options
    notif[1]['payload']['image_meta']['org.openstack__1__architecture'] = os_architecture
    notif[1]['payload']['image_meta']['org.openstack__1__os_distro'] = os_distro
    notif[1]['payload']['image_meta']['org.openstack__1__os_version'] = os_version

    return notif


def create_raw(mox, when, event, instance=INSTANCE_ID_1,
               request_id=REQUEST_ID_1, state='active', old_task='',
               host='c.example.com', service='compute', json_str=''):
    raw = mox.CreateMockAnything()
    raw.host = host
    raw.service = service
    raw.instance = instance
    raw.event = event
    raw.when = when
    raw.state = state
    raw.old_task = old_task
    raw.request_id = request_id
    raw.json = json_str
    return raw


def create_lifecycle(mox, instance, last_state, last_task_state, last_raw):
    lifecycle = mox.CreateMockAnything()
    lifecycle.instance = instance
    lifecycle.last_state = last_state
    lifecycle.last_task_state = last_task_state
    lifecycle.last_raw = last_raw
    return lifecycle


def create_timing(mox, name, lifecycle, start_raw=None, start_when=None,
                  end_raw=None, end_when=None, diff=None):
    timing = mox.CreateMockAnything()
    timing.name = name
    timing.lifecycle = lifecycle
    timing.start_raw = start_raw
    timing.start_when = start_when
    timing.end_raw = end_raw
    timing.end_when = end_when
    timing.diff = diff
    return timing


def create_tracker(mox, request_id, lifecycle, start, last_timing=None,
                   duration=str(0.0)):
    tracker = mox.CreateMockAnything()
    tracker.request_id=request_id
    tracker.lifecycle=lifecycle
    tracker.start=start
    tracker.last_timing=last_timing
    tracker.duration=duration
    return tracker


class FakeVerifierConfig(object):
    def __init__(self, host, port, virtual_host, userid, password, tick_time,
                 settle_time, settle_units, durable_queue, topics, notifs,
                 nova_event_type, glance_event_type, flavor_field_name):
        self.host = lambda: host
        self.port = lambda: port
        self.virtual_host = lambda: virtual_host
        self.userid = lambda: userid
        self.password = lambda: password
        self.pool_size = lambda: 5
        self.tick_time = lambda: tick_time
        self.settle_time = lambda: settle_time
        self.settle_units = lambda: settle_units
        self.durable_queue = lambda: durable_queue
        self.topics = lambda: topics
        self.enable_notifications = lambda: notifs
        self.validation_level = lambda: 'all'
        self.nova_event_type = lambda: nova_event_type
        self.glance_event_type = lambda: glance_event_type
        self.flavor_field_name = lambda: flavor_field_name


def make_verifier_config(notifs):
        topics = {'exchange': ['notifications.info']}
        config = FakeVerifierConfig(HOST, PORT, VIRTUAL_HOST, USERID,
                                    PASSWORD, TICK_TIME, SETTLE_TIME,
                                    SETTLE_UNITS, True, topics, notifs,
                                    NOVA_VERIFIER_EVENT_TYPE,
                                    GLANCE_VERIFIER_EVENT_TYPE,
                                    FLAVOR_FIELD_NAME)
        return config