import datetime
import os
import signal
import sys
import time

from multiprocessing import Process, Manager

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from stacktach import db, stacklog
from django.db import close_connection

import worker.worker as worker
from worker import config

processes = {}
log_listener = None
stacklog.set_default_logger_name('worker')

DEFAULT_PROC_TIMEOUT = 600
RUNNING = True

def _get_parent_logger():
    return stacklog.get_logger('worker', is_parent=True)


def create_proc_table(manager):
    for deployment in config.deployments():
        if deployment.get('enabled', True):
            name = deployment['name']
            db_deployment, new = db.get_or_create_deployment(name)
            for exchange in deployment.get('topics').keys():
                stats = manager.dict()
                proc_info = dict(process=None,
                                 pid=0,
                                 deployment=deployment,
                                 deploy_id=db_deployment.id,
                                 exchange=exchange,
                                 stats=stats)
                processes[(name, exchange)] = proc_info


def is_alive(proc_info):
    process = proc_info['process']
    if not proc_info['pid'] or process is None:
        return False
    return process.is_alive()


def needs_restart(proc_info):
    timeout = config.workers().get('process_timeout', DEFAULT_PROC_TIMEOUT)
    process = proc_info['process']
    stats = proc_info['stats']
    age = datetime.datetime.utcnow() - stats['timestamp']
    if age > datetime.timedelta(seconds=timeout):
        process.terminate()
        return True
    return False


def start_proc(proc_info):
    logger = _get_parent_logger()
    if is_alive(proc_info):
        if needs_restart(proc_info):
            logger.warning("Child process %s (%s %s) terminated due to "
                "heartbeat timeout. Restarting..." % (proc_info['pid'],
                proc_info['deployment']['name'], proc_info['exchange']))
        else:
            return False
    stats = proc_info['stats']
    stats['timestamp'] = datetime.datetime.utcnow()
    stats['total_processed'] = 0
    stats['processed'] = 0
    args = (proc_info['deployment'], proc_info['deploy_id'],
            proc_info['exchange'], stats)
    process = Process(target=worker.run, args=args)
    process.daemon = True
    process.start()
    proc_info['pid'] = process.pid
    proc_info['process'] = process
    logger.info("Started child process %s (%s %s)" % (proc_info['pid'],
        proc_info['deployment']['name'], proc_info['exchange']))
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
    logger = _get_parent_logger()
    log_listener = stacklog.LogListener(logger)
    log_listener.start()
    manager = Manager()

    create_proc_table(manager)

    # NOTE (apmelton)
    # Close the connection before spinning up the child process,
    # otherwise the child process will attempt to use the connection
    # the parent process opened up to get/create the deployment.
    close_connection()

    signal.signal(signal.SIGINT, kill_time)
    signal.signal(signal.SIGTERM, kill_time)

    logger.info("Starting Workers...")
    while RUNNING:
        check_or_start_all()
        time.sleep(30)
    logger.info("Workers Shutting down...")

    #make sure.
    stop_all()

    log_listener.end()
    sys.exit(0)

