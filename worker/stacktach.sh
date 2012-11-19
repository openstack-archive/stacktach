#!/bin/bash

WORKDIR=/srv/www/stacktach/app
DAEMON=/usr/bin/python
ARGS=$WORKDIR/worker/start_workers.py
PIDFILE=/var/run/stacktach.pid

case "$1" in
  start)
    echo "Starting server"
    cd $WORKDIR
    source etc/stacktach_config.sh
    /sbin/start-stop-daemon --start --pidfile $PIDFILE --make-pidfile -b --exec $DAEMON $ARGS
    ;;
  stop)
    echo "Stopping server"
    /sbin/start-stop-daemon --stop --pidfile $PIDFILE --verbose
    ;;
  *)
    echo "Usage: stacktach.sh {start|stop}"
    exit 1
    ;;
esac

exit 0
