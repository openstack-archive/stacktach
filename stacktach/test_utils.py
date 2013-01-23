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

def make_create_start_json(instance_type_id='1',
                           instance_id=INSTANCE_ID_1,
                           request_id=REQUEST_ID_1):
    notification = ['monitor.info', {
        '_context_request_id': request_id,
        'event_type': views.INSTANCE_EVENT['create_start'],
        'payload': {
            'instance_id': instance_id,
            'instance_type_id': instance_type_id,
            }
    }
    ]

    return json.dumps(notification)

def make_create_end_json(launched_at, instance_type_id='1',
                         instance_id=INSTANCE_ID_1,
                         request_id=REQUEST_ID_1):
    notification = ['monitor.info', {
        '_context_request_id': request_id,
        'event_type': views.INSTANCE_EVENT['create_end'],
        'payload': {
            'instance_id': instance_id,
            'instance_type_id': instance_type_id,
            'launched_at': launched_at
        }
    }
    ]

    return json.dumps(notification)

def make_delete_end_json(launched_at, deleted_at,
                         instance_type_id='1', instance_id=INSTANCE_ID_1,
                         request_id=REQUEST_ID_2):
    notification = ['monitor.info', {
        '_context_request_id': request_id,
        'event_type': views.INSTANCE_EVENT['create_end'],
        'payload': {
            'instance_id': instance_id,
            'instance_type_id': instance_type_id,
            'launched_at': launched_at,
            'deleted_at': deleted_at
        }
    }
    ]

    return json.dumps(notification)

def make_exists_json(launched_at, instance_type_id='1',
                     instance_id=INSTANCE_ID_1, deleted_at=None):
    notification = ['monitor.info', {
        'message_id': MESSAGE_ID_1,
        'event_type': views.INSTANCE_EVENT['create_end'],
        'payload': {
            'instance_id': instance_id,
            'instance_type_id': instance_type_id,
            'launched_at': launched_at,
            }
    }
    ]

    if deleted_at:
        notification[1]['payload']['deleted_at'] = deleted_at

    return json.dumps(notification)

def make_resize_finish_json(launched_at, instance_type_id='2',
                            instance_id=INSTANCE_ID_1,
                            request_id=REQUEST_ID_1):
    notification = ['monitor.info', {
        '_context_request_id': request_id,
        'event_type': views.INSTANCE_EVENT['resize_finish_end'],
        'payload': {
            'instance_id': instance_id,
            'instance_type_id': instance_type_id,
            'launched_at': launched_at
        }
    }
    ]

    return json.dumps(notification)

def make_resize_prep_start_json(instance_type_id='1',
                                instance_id=INSTANCE_ID_1,
                                request_id=REQUEST_ID_1):
    notification = ['monitor.info', {
        '_context_request_id': request_id,
        'event_type': views.INSTANCE_EVENT['resize_prep_start'],
        'payload': {
            'instance_id': instance_id,
            'instance_type_id': instance_type_id,
            }
    }
    ]

    return json.dumps(notification)

def make_resize_prep_end_json(instance_type_id='1',
                              new_instance_type_id='2',
                              instance_id=INSTANCE_ID_1,
                              request_id=REQUEST_ID_1):
    notification = ['monitor.info', {
        '_context_request_id': request_id,
        'event_type': views.INSTANCE_EVENT['resize_prep_start'],
        'payload': {
            'instance_id': instance_id,
            'instance_type_id': instance_type_id,
            'new_instance_type_id': new_instance_type_id,
            }
    }
    ]

    return json.dumps(notification)

def make_resize_revert_start_json(instance_type_id='2',
                                  instance_id=INSTANCE_ID_1,
                                  request_id=REQUEST_ID_1):
    notification = ['monitor.info', {
        '_context_request_id': request_id,
        'event_type': views.INSTANCE_EVENT['resize_revert_start'],
        'payload': {
            'instance_id': instance_id,
            'instance_type_id': instance_type_id,
            }
    }
    ]

    return json.dumps(notification)

def make_resize_revert_end_json(launched_at, instance_type_id='1',
                                instance_id=INSTANCE_ID_1,
                                request_id=REQUEST_ID_1):
    notification = ['monitor.info', {
        '_context_request_id': request_id,
        'event_type': views.INSTANCE_EVENT['resize_finish_end'],
        'payload': {
            'instance_id': instance_id,
            'instance_type_id': instance_type_id,
            'launched_at': launched_at
        }
    }
    ]

    return json.dumps(notification)

def create_raw(deployment, when, event, instance=INSTANCE_ID_1,
               request_id=REQUEST_ID_1, state='active', old_task='',
               host='compute', json=''):
    raw_values  = {
        'deployment': deployment,
        'host': host,
        'state': state,
        'old_task': old_task,
        'when': when,
        'event': event,
        'instance': instance,
        'request_id': request_id,
        'json': json
    }
    raw = RawData(**raw_values)
    raw.save()
    return raw