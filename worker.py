# Copyright 2012 - Dark Secret Software Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This is the worker you run in your OpenStack environment. You need
# to set TENANT_ID and URL to point to your StackTach web server.

import json
import kombu
import kombu.connection
import kombu.entity
import kombu.mixins
import threading
import urllib
import urllib2

# CHANGE THESE FOR YOUR INSTALLATION ...
TENANT_ID = 1
URL = 'http://darksecretsoftware.com/stacktach/%d/data/' % TENANT_ID
RABBIT_HOST = "localhost"
RABBIT_PORT = 5672
RABBIT_USERID = "guest"
RABBIT_PASSWORD = "guest"
RABBIT_VIRTUAL_HOST = "/"

try:
    from worker_conf import *
except ImportError:
    pass

# For now we'll just grab all the fanout messages from compute to scheduler ...
scheduler_exchange = kombu.entity.Exchange("scheduler_fanout", type="fanout",
                                      durable=False, auto_delete=True,
                                      exclusive=True)

scheduler_queues = [
        # The Queue name has to be unique or we we'll end up with Round Robin
        # behavior from Rabbit, even though it's a Fanout queue. In Nova the
        # queues have UUID's tacked on the end.
        kombu.Queue("scheduler.xxx", scheduler_exchange, durable=False,
                    auto_delete=False),
    ]

nova_exchange = kombu.entity.Exchange("nova", type="topic",
                                      durable=True, auto_delete=False,
                                      exclusive=False)

nova_queues = [
        kombu.Queue("monitor", nova_exchange, durable=False, auto_delete=False,
                    exclusive=False, routing_key='monitor.*'),
    ]


class SchedulerFanoutConsumer(kombu.mixins.ConsumerMixin):
    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=scheduler_queues,
                         callbacks=[self.on_scheduler]),
                Consumer(queues=nova_queues, callbacks=[self.on_nova])]

    def _process(self, body, message):
        routing_key = message.delivery_info['routing_key']
        payload = (routing_key, body)
        jvalues = json.dumps(payload)

        try:
            raw_data = dict(args=jvalues)
            cooked_data = urllib.urlencode(raw_data)
            req = urllib2.Request(URL, cooked_data)
            response = urllib2.urlopen(req)
            page = response.read()
            print page
        except urllib2.HTTPError, e:
            if e.code == 401:
                print "Unauthorized. Correct tenant id of %d?" % TENANT_ID
            print e
            page = e.read()
            print page
            raise

    def on_scheduler(self, body, message):
        # Uncomment if you want periodic compute node status updates.
        #self._process(body, message)
        message.ack()

    def on_nova(self, body, message):
        self._process(body, message)
        message.ack()


if __name__ == "__main__":
    print "StackTach", URL
    print "Rabbit", RABBIT_HOST, RABBIT_PORT, RABBIT_USERID, RABBIT_VIRTUAL_HOST

    params = dict(hostname=RABBIT_HOST,
                  port=RABBIT_PORT,
                  userid=RABBIT_USERID,
                  password=RABBIT_PASSWORD,
                  virtual_host=RABBIT_VIRTUAL_HOST)

    with kombu.connection.BrokerConnection(**params) as conn:
        consumer = SchedulerFanoutConsumer(conn)
        try:
            print "Listening"
            consumer.run()
        except KeyboardInterrupt:
            print("bye bye")
