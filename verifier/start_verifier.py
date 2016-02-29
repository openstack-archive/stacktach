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
import time
import datetime

from multiprocessing import Process, Manager

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

processes = {}
log_listener = None
stacklog.set_default_logger_name('verifier')

DEFAULT_PROC_TIMEOUT = 3600
RUNNING = True

def _get_parent_logger():
    return stacklog.get_logger('verifier', is_parent=True)


def _load_nova_reconciler():
    config_loc = verifier_config.reconciler_config()
    with open(config_loc, 'r') as rec_config_file:
        rec_config = json.load(rec_config_file)
        return reconciler.Reconciler(rec_config)


def make_and_start_verifier(exchange, stats=None):
    # Gotta create it and run it this way so things don't get
    # lost when the process is forked.
    verifier = None
    if exchange == "nova":
        reconcile = verifier_config.reconcile()
        reconciler = None
        if reconcile:
            reconciler = _load_nova_reconciler()
        verifier = nova_verifier.NovaVerifier(verifier_config,
                                              reconciler=reconciler,
                                              stats=stats)
    elif exchange == "glance":
        verifier = glance_verifier.GlanceVerifier(verifier_config,
                                                  stats=stats)

    verifier.run()


def create_proc_table(manager):
    for exchange in verifier_config.topics().keys():
        stats = manager.dict()
        proc_info = dict(process=None,
                         pid=0,
                         exchange=exchange,
                         stats=stats)
        processes[exchange] = proc_info


def is_alive(proc_info):
    process = proc_info['process']
    if not proc_info['pid'] or process is None:
        return False
    return process.is_alive()


def needs_restart(proc_info):
    timeout = verifier_config.process_timeout(DEFAULT_PROC_TIMEOUT)
    process = proc_info['process']
    stats = proc_info['stats']
    age = datetime.datetime.utcnow() - stats['timestamp']
    if timeout and (age > datetime.timedelta(seconds=timeout)):
        process.terminate()
        return True
    return False


def start_proc(proc_info):
    logger = _get_parent_logger()
    if is_alive(proc_info):
        if needs_restart(proc_info):
            logger.warning("Child process %s (%s) terminated due to "
                "heartbeat timeout. Restarting..." % (proc_info['pid'],
                proc_info['exchange']))
        else:
            return False
    stats = proc_info['stats']
    stats['timestamp'] = datetime.datetime.utcnow()
    stats['total_processed'] = 0
    stats['processed'] = 0
    args = (proc_info['exchange'], stats)
    process = Process(target=make_and_start_verifier, args=args)
    process.start()
    proc_info['pid'] = process.pid
    proc_info['process'] = process
    logger.info("Started child process %s (%s)" % (proc_info['pid'],
        proc_info['exchange']))
    return True


def check_or_start_all():
    for proc_name in sorted(processes.keys()):
        if RUNNING:
            start_proc(processes[proc_name])


def stop_all():
    procs = sorted(processes.keys())
    for pname in procs:
        process = processes[pname]['process']
        if process is not None:
            process.terminate()
    for pname in procs:
        process = processes[pname]['process']
        if process is not None:
            process.join()
        processes[pname]['process'] = None
        processes[pname]['pid'] = 0


def kill_time(signal, frame):
    global RUNNING
    RUNNING = False
    stop_all()


if __name__ == '__main__':
    verifier_config.load()

    logger = _get_parent_logger()
    log_listener = stacklog.LogListener(logger)
    log_listener.start()
    manager = Manager()

    create_proc_table(manager)

    signal.signal(signal.SIGINT, kill_time)
    signal.signal(signal.SIGTERM, kill_time)

    logger.info("Starting Verifiers...")
    while RUNNING:
        check_or_start_all()
        time.sleep(30)
    logger.info("Verifiers Shutting down...")

    #make sure.
    stop_all()

    log_listener.end()
    sys.exit(0)
