import json
import os
import signal
import sys

from multiprocessing import Process

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

import worker

config_filename = os.environ.get('STACKTACH_DEPLOYMENTS_FILE',
                                 'stacktach_worker_config.json')
try:
    from local_settings import *
    config_filename = STACKTACH_DEPLOYMENTS_FILE
except ImportError:
    pass

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


if __name__ == '__main__':
    config = None
    with open(config_filename, "r") as f:
        config = json.load(f)

    deployments = config['deployments']

    for deployment in deployments:
        if deployment.get('enabled', True):
            process = Process(target=worker.run, args=(deployment,))
            process.daemon = True
            process.start()
            processes.append(process)
    signal.signal(signal.SIGINT, kill_time)
    signal.signal(signal.SIGTERM, kill_time)
    signal.pause()
