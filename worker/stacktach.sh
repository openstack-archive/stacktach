#!/bin/sh
### BEGIN INIT INFO
# Provides:          stacktach
# Required-Start:
# Required-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start/stop stacktach workers 
### END INIT INFO

. /lib/lsb/init-functions

WORKDIR=/srv/www/stacktach/app
DAEMON=/usr/bin/python
ARGS=$WORKDIR/worker/start_workers.py
PIDFILE=/var/run/stacktach.pid

export DJANGO_SETTINGS_MODULE="settings"

case "$1" in
  start)
    echo "Starting stacktach workers"
    cd $WORKDIR
    /sbin/start-stop-daemon --start --pidfile $PIDFILE --make-pidfile -b --exec $DAEMON $ARGS
    ;;
  stop)
    echo "Stopping stacktach workers"
    /sbin/start-stop-daemon --stop --pidfile $PIDFILE --verbose
    ;;
  restart)
    echo "Restarting stacktach workers"
    /sbin/start-stop-daemon --stop --pidfile $PIDFILE  --retry 5
    /sbin/start-stop-daemon --start --pidfile $PIDFILE --make-pidfile -b --exec $DAEMON $ARGS
    ;;
  status)
    status_of_proc "$DAEMON" "stacktach" && exit 0 || exit $?
    ;;
  *)
    echo "Usage: stacktach.sh {start|stop|restart|status}"
    exit 1
    ;;
esac

exit 0
