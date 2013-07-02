import os
import signal
import sys

from multiprocessing import Process

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

import worker.worker as worker
from worker import config

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

    for deployment in config.deployments():
        if deployment.get('enabled', True):
            for exchange in deployment.get('topics').keys():
                process = Process(target=worker.run, args=(deployment,
                                                           exchange,))
                process.daemon = True
                process.start()
                processes.append(process)
    signal.signal(signal.SIGINT, kill_time)
    signal.signal(signal.SIGTERM, kill_time)
    signal.pause()
