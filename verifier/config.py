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
import os

config_filename = os.environ.get('STACKTACH_VERIFIER_CONFIG',
                                 'stacktach_verifier_config.json')
try:
    from local_settings import *
    config_filename = STACKTACH_VERIFIER_CONFIG
except ImportError:
    pass

config = None


def load():
    global config
    with open(config_filename, "r") as f:
        config = json.load(f)


def enable_notifications():
    return config['enable_notifications']


def topics():
    return config['rabbit']['topics']


def tick_time():
    return config['tick_time']


def settle_units():
    return config['settle_units']


def settle_time():
    return config['settle_time']


def reconcile():
    return config.get('reconcile', False)


def reconciler_config():
    return config.get(
        'reconciler_config', '/etc/stacktach/reconciler_config.json')

def pool_size():
    return config['pool_size']


def process_timeout(default=0):
    return config.get('process_timeout', default)


def durable_queue():
    return config['rabbit']['durable_queue']


def host():
    return config['rabbit']['host']


def port():
    return config['rabbit']['port']


def userid():
    return config['rabbit']['userid']


def password():
    return config['rabbit']['password']


def virtual_host():
    return config['rabbit']['virtual_host']


def validation_level():
    return config['validation_level']


def nova_event_type():
    return config.get('nova_event_type', 'compute.instance.exists.verified')


def glance_event_type():
    return config.get('glance_event_type', 'image.exists.verified')


def flavor_field_name():
    return config['flavor_field_name']
