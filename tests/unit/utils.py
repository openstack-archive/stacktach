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

TENANT_ID_1 = 'testtenantid1'
TENANT_ID_2 = 'testtenantid2'

from stacktach import datetime_to_decimal as dt

INSTANCE_ID_1 = "08f685d9-6352-4dbc-8271-96cc54bf14cd"
INSTANCE_ID_2 = "515adf96-41d3-b86d-5467-e584edc61dab"

INSTANCE_TYPE_ID_1 = "12345"
INSTANCE_TYPE_ID_2 = '54321'

DUMMY_TIME = datetime.datetime.utcnow()

MESSAGE_ID_1 = "7f28f81b-29a2-43f2-9ba1-ccb3e53ab6c8"
MESSAGE_ID_2 = "4d596126-0f04-4329-865f-7b9a7bd69bcf"

REQUEST_ID_1 = 'req-611a4d70-9e47-4b27-a95e-27996cc40c06'
REQUEST_ID_2 = 'req-a951dec0-52ee-425d-9f56-d68bd1ad00ac'
REQUEST_ID_3 = 'req-039a33f7-5849-4406-8166-4db8cd085f52'


def decimal_utc(t = datetime.datetime.utcnow()):
    return dt.dt_to_decimal(t)


def create_nova_notif(request_id=None, instance=INSTANCE_ID_1, type_id='1',
                      launched=None, deleted=None, new_type_id=None,
                      message_id=MESSAGE_ID_1, audit_period_beginning=None,
                      audit_period_ending=None, tenant_id = None):
    notif = ['', {
        'message_id': message_id,
        'payload': {
            'instance_id': instance,
            'instance_type_id': type_id,
            }
    }]

    if request_id:
        notif[1]['_context_request_id'] = request_id
    if launched:
        notif[1]['payload']['launched_at'] = launched
    if deleted:
        notif[1]['payload']['deleted_at'] = deleted
    if new_type_id:
        notif[1]['payload']['new_instance_type_id'] = new_type_id
    if audit_period_beginning:
        notif[1]['payload']['audit_period_beginning'] = audit_period_beginning
    if audit_period_ending:
        notif[1]['payload']['audit_period_ending'] = audit_period_ending
    if tenant_id:
        notif[1]['payload']['tenant_id'] = tenant_id

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