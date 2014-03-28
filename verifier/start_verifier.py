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
import signal
import sys

from multiprocessing import Process

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)
from stacktach import stacklog
from stacktach import reconciler
from verifier import nova_verifier
from verifier import glance_verifier
import verifier.config as verifier_config

try:
    from local_settings import *
    config_filename = STACKTACH_VERIFIER_CONFIG
except ImportError:
    pass

process = None
log_listener = None
processes = []
stacklog.set_default_logger_name('verifier')

def _get_parent_logger():
    return stacklog.get_logger('verifier', is_parent=True)


def kill_time(signal, frame):
    log_listener.end()
    print "dying ..."
    for process in processes:
        process.terminate()
    print "rose"
    for process in processes:
        process.join()
    print "bud"
    sys.exit(0)


def _load_nova_reconciler():
    config_loc = verifier_config.reconciler_config()
    with open(config_loc, 'r') as rec_config_file:
        rec_config = json.load(rec_config_file)
        return reconciler.Reconciler(rec_config)

if __name__ == '__main__':
    def make_and_start_verifier(exchange):
        # Gotta create it and run it this way so things don't get
        # lost when the process is forked.
        verifier = None
        if exchange == "nova":
            reconcile = verifier_config.reconcile()
            reconciler = None
            if reconcile:
                reconciler = _load_nova_reconciler()
            verifier = nova_verifier.NovaVerifier(verifier_config,
                                                  reconciler=reconciler)
        elif exchange == "glance":
            verifier = glance_verifier.GlanceVerifier(verifier_config)

        verifier.run()

    verifier_config.load()
    log_listener = stacklog.LogListener(_get_parent_logger())
    log_listener.start()
    for exchange in verifier_config.topics().keys():
        process = Process(target=make_and_start_verifier, args=(exchange,))
        process.start()
        processes.append(process)

    if len(processes) > 0:
        # Only pause parent process if there are children running.
        # Otherwise just end...
        signal.signal(signal.SIGINT, kill_time)
        signal.signal(signal.SIGTERM, kill_time)
        signal.pause()
