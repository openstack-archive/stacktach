#!/bin/bash

WORKDIR=/srv/www/stacktach/django/stproject/
DAEMON=/usr/bin/python
ARGS=$WORKDIR/worker/start_workers.py
PIDFILE=/var/run/stacktach.pid

export DJANGO_SETTINGS_MODULE="settings"

case "$1" in
  start)
    echo "Starting server"
    cd $WORKDIR
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
