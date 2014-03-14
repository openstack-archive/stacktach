#!/bin/sh
### BEGIN INIT INFO
# Provides:          verifier
# Required-Start:
# Required-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start/stop stacktach verifier
### END INIT INFO

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

. /lib/lsb/init-functions

WORKDIR=/srv/www/stacktach/app
DAEMON=/usr/bin/python
ARGS=$WORKDIR/verifier/start_verifier.py
PIDFILE=/var/run/stacktach_verifier.pid

export DJANGO_SETTINGS_MODULE="settings"

case "$1" in
  start)
    echo "Starting stacktach verifier"
    cd $WORKDIR
    /sbin/start-stop-daemon --start --pidfile $PIDFILE --make-pidfile -b --exec $DAEMON $ARGS
    ;;
  stop)
    echo "Stopping stacktach verifier"
    /sbin/start-stop-daemon --stop --pidfile $PIDFILE --verbose
    ;;
  restart)
    echo "Restarting stacktach verifier"
    /sbin/start-stop-daemon --stop --pidfile $PIDFILE  --retry 5
    /sbin/start-stop-daemon --start --pidfile $PIDFILE --make-pidfile -b --exec $DAEMON $ARGS
    ;;
  status)
    status_of_proc -p "${PIDFILE}" "$DAEMON" "verifier" && exit 0 || exit $?
    ;;
  *)
    echo "Usage: verifier.sh {start|stop|restart|status}"
    exit 1
    ;;
esac

exit 0
