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

import os
import signal
import sys

from multiprocessing import Process

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

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

processes = []


def kill_time(signal, frame):
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
