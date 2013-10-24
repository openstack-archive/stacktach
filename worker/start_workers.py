import os
import signal
import sys

from multiprocessing import Process

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from stacktach import db
from django.db import close_connection

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
            db_deployment, new = db.get_or_create_deployment(deployment['name'])
            # NOTE (apmelton)
            # Close the connection before spinning up the child process,
            # otherwise the child process will attempt to use the connection
            # the parent process opened up to get/create the deployment.
            close_connection()
            for exchange in deployment.get('topics').keys():
                process = Process(target=worker.run, args=(deployment,
                                                           db_deployment.id,
                                                           exchange,))
                process.daemon = True
                process.start()
                processes.append(process)
    signal.signal(signal.SIGINT, kill_time)
    signal.signal(signal.SIGTERM, kill_time)
    signal.pause()
