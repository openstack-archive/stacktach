#!/bin/bash

WORKDIR=/srv/www/stacktach/app
DAEMON=/usr/bin/python
ARGS=$WORKDIR/verifier/start_verifier.py
PIDFILE=/var/run/stacktach_verifier.pid

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
    echo "Usage: verifier.sh {start|stop}"
    exit 1
    ;;
esac

exit 0
