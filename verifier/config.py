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
