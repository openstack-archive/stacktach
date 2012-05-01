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

import daemon
import json
import kombu
import kombu.connection
import kombu.entity
import kombu.mixins
import logging
import threading
import time
import urllib
import urllib2


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
handler = logging.handlers.TimedRotatingFileHandler('worker.log',
                                           when='h', interval=6, backupCount=4)
LOG.addHandler(handler)


# CHANGE THESE FOR YOUR INSTALLATION ...
DEPLOYMENTS = [
    dict(
        tenant_id=1,
        url='http://example.com',
        rabbit_host="localhost",
        rabbit_port=5672,
        rabbit_userid="guest",
        rabbit_password="guest",
        rabbit_virtual_host="/"),
    ]

try:
    from worker_conf import *
except ImportError:
    pass


# For now we'll just grab all the fanout messages from compute to scheduler ...
#scheduler_exchange = kombu.entity.Exchange("scheduler_fanout", type="fanout",
#                                      durable=False, auto_delete=True,
#                                      exclusive=True)
#
#scheduler_queues = [
        # The Queue name has to be unique or we we'll end up with Round Robin
        # behavior from Rabbit, even though it's a Fanout queue. In Nova the
        # queues have UUID's tacked on the end.
#        kombu.Queue("scheduler.xxx", scheduler_exchange, durable=False,
#                    auto_delete=True),
#    ]

nova_exchange = kombu.entity.Exchange("nova", type="topic", exclusive=False,
                                      durable=True, auto_delete=False)

nova_queues = [
        kombu.Queue("monitor.info", nova_exchange, durable=True, auto_delete=False,
                    exclusive=False, routing_key='monitor.info'),
        kombu.Queue("monitor.error", nova_exchange, durable=True, auto_delete=False,
                    exclusive=False, routing_key='monitor.error'),
    ]


class NovaConsumer(kombu.mixins.ConsumerMixin):
    def __init__(self, connection, url):
        self.connection = connection
        self.url = url

    def get_consumers(self, Consumer, channel):
        return [#Consumer(queues=scheduler_queues,
                #         callbacks=[self.on_scheduler]),
                Consumer(queues=nova_queues, callbacks=[self.on_nova])]

    def _process(self, body, message):
        routing_key = message.delivery_info['routing_key']
        payload = (routing_key, body)
        jvalues = json.dumps(payload)

        try:
            raw_data = dict(args=jvalues)
            cooked_data = urllib.urlencode(raw_data)
            req = urllib2.Request(self.url, cooked_data)
            response = urllib2.urlopen(req)
            LOG.debug("Sent %s to %s", routing_key, self.url)
            #page = response.read()
            #print page
        except urllib2.HTTPError, e:
            if e.code == 401:
                LOG.debug("Unauthorized. Correct URL? %s" % self.url)
            LOG.exception(e)
            page = e.read()
            LOG.debug(page)
            raise

    def on_scheduler(self, body, message):
        # Uncomment if you want periodic compute node status updates.
        #self._process(body, message)
        message.ack()
        LOG.debug("SCHEDULER ACKED")

    def on_nova(self, body, message):
        self._process(body, message)
        message.ack()


class Monitor(threading.Thread):
    def __init__(self, deployment):
        super(Monitor, self).__init__()
        self.deployment = deployment

    def run(self):
        tenant_id = self.deployment.get('tenant_id', 1)
        url = self.deployment.get('url', 'http://www.example.com')
        url = "%s/%d/data/" % (url, tenant_id)
        host = self.deployment.get('rabbit_host', 'localhost')
        port = self.deployment.get('rabbit_port', 5672)
        user_id = self.deployment.get('rabbit_userid', 'rabbit')
        password = self.deployment.get('rabbit_password', 'rabbit')
        virtual_host = self.deployment.get('rabbit_virtual_host', '/')

        LOG.info("StackTach %s" % url)
        LOG.info("Rabbit: %s %s %s %s" % 
                                (host, port, user_id, virtual_host))

        params = dict(hostname=host,
                      port=port,
                      userid=user_id,
                      password=password,
                      virtual_host=virtual_host)

        while True:
            with kombu.connection.BrokerConnection(**params) as conn:
                try:
                    consumer = NovaConsumer(conn, url)
                    consumer.run()
                except Exception as e:
                    LOG.exception("url=%s, exception=%s. Reconnecting in 5s" % (url, e))
                    time.sleep(5)


#with daemon.DaemonContext(files_preserve=[handler.stream]):
if True:
    workers = []
    for deployment in DEPLOYMENTS:
        LOG.info("Starting deployment: %s", deployment)
        monitor = Monitor(deployment)
        workers.append(monitor)
        try:
            monitor.start()
        except Exception as e:
            LOG.exception("Deployment: %s, Exception: %s" % (deployment, e))

    for worker in workers:
        LOG.info("Attempting to join to %s" % worker.deployment)
        worker.join()
        LOG.info("Joined to %s" % worker.deployment)
