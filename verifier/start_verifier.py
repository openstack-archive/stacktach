import json
import os
import signal
import sys

from multiprocessing import Process

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from verifier import dbverifier

config_filename = os.environ.get('STACKTACH_VERIFIER_CONFIG',
                                 'stacktach_verifier_config.json')
try:
    from local_settings import *
    config_filename = STACKTACH_VERIFIER_CONFIG
except ImportError:
    pass

process = None


def kill_time(signal, frame):
    print "dying ..."
    if process:
        process.terminate()
    print "rose"
    if process:
        process.join()
    print "bud"
    sys.exit(0)


if __name__ == '__main__':
    config = None
    with open(config_filename, "r") as f:
        config = json.load(f)

    process = Process(target=dbverifier.run, args=(config, ))
    process.start()
    signal.signal(signal.SIGINT, kill_time)
    signal.signal(signal.SIGTERM, kill_time)
    signal.pause()
