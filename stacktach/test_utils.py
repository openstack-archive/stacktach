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

import json
import views

from models import *

INSTANCE_ID_1 = 'testinstanceid1'
INSTANCE_ID_2 = 'testinstanceid2'

MESSAGE_ID_1 = 'testmessageid1'
MESSAGE_ID_2 = 'testmessageid2'

REQUEST_ID_1 = 'testrequestid1'
REQUEST_ID_2 = 'testrequestid2'
REQUEST_ID_3 = 'testrequestid3'


def create_raw(deployment, when, event, instance=INSTANCE_ID_1,
               request_id=REQUEST_ID_1, state='active', old_task='',
               host='compute', service='compute', json='',
               tenant='default_tenant_id'):
    raw_values  = {
        'deployment': deployment,
        'host': host,
        'service': service,
        'state': state,
        'old_task': old_task,
        'when': when,
        'event': event,
        'instance': instance,
        'request_id': request_id,
        'json': json,
        'tenant': tenant
    }
    raw = RawData(**raw_values)
    raw.save()
    return raw