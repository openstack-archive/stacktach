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
