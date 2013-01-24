import datetime
import os
import sys
import unittest

INSTANCE_ID_1 = 'testinstanceid1'
INSTANCE_ID_2 = 'testinstanceid2'

MESSAGE_ID_1 = 'testmessageid1'
MESSAGE_ID_2 = 'testmessageid2'

REQUEST_ID_1 = 'testrequestid1'
REQUEST_ID_2 = 'testrequestid2'
REQUEST_ID_3 = 'testrequestid3'

def setup_sys_path():
    sys.path = [os.path.abspath(os.path.dirname('stacktach'))] + sys.path

def setup_environment():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    os.environ['STACKTACH_DB_ENGINE'] = 'django.db.backends.sqlite3'
    when = str(datetime.datetime.utcnow())
    os.environ['STACKTACH_DB_NAME'] = '/tmp/stacktach.%s.sqlite' % when
    os.environ['STACKTACH_DB_HOST'] = ''
    os.environ['STACKTACH_DB_USERNAME'] = ''
    os.environ['STACKTACH_DB_PASSWORD'] = ''
    install_dir = os.path.abspath(os.path.dirname('stacktach'))
    os.environ['STACKTACH_INSTALL_DIR'] = install_dir

setup_sys_path()
setup_environment()
from stacktach import datetime_to_decimal as dt

def decimal_utcnow():
    return dt.dt_to_decimal(datetime.datetime.utcnow())

def create_raw(mox, when, event, instance=INSTANCE_ID_1,
               request_id=REQUEST_ID_1, state='active', old_task='',
               host='compute', json=''):
    raw = mox.CreateMockAnything()
    raw.host = host
    raw.instance = instance
    raw.event = event
    raw.when = when
    raw.state = state
    raw.old_task = old_task
    raw.request_id = request_id
    raw.json = json
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