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
import logging
import time

from stacktach import models, views
from stacktach import datetime_to_decimal as dt


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
handler = logging.handlers.TimedRotatingFileHandler('worker.log',
                                           when='h', interval=6, backupCount=4)
LOG.addHandler(handler)

nova_exchange = kombu.entity.Exchange("nova", type="topic", exclusive=False,
                                      durable=True, auto_delete=False)

nova_queues = [
    kombu.Queue("monitor.info", nova_exchange, durable=True,
                auto_delete=False,
                exclusive=False, routing_key='monitor.info'),
    kombu.Queue("monitor.error", nova_exchange, durable=True,
                auto_delete=False,
                exclusive=False, routing_key='monitor.error'),
]


class NovaConsumer(kombu.mixins.ConsumerMixin):
    def __init__(self, name, connection, deployment):
        self.connection = connection
        self.deployment = deployment
        self.name = name

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=nova_queues, callbacks=[self.on_nova])]

    def _process(self, body, message):
        routing_key = message.delivery_info['routing_key']
        payload = (routing_key, body)
        jvalues = json.dumps(payload)

        args = (routing_key, json.loads(message.body))
        asJson = json.dumps(args)

        raw = views.process_raw_data(self.deployment, args, asJson)
        if not raw:
            LOG.debug("No record from %s", routing_key)
        else:
            LOG.debug("Recorded rec# %d from %s/%s at %s (%.6f)" %
                          (raw.id, self.name, routing_key,
                           str(dt.dt_from_decimal(raw.when)),
                           float(raw.when)))

    def on_nova(self, body, message):
        self._process(body, message)
        message.ack()


def run(deployment_config):
    name = deployment_config['name']
    host = deployment_config.get('rabbit_host', 'localhost')
    port = deployment_config.get('rabbit_port', 5672)
    user_id = deployment_config.get('rabbit_userid', 'rabbit')
    password = deployment_config.get('rabbit_password', 'rabbit')
    virtual_host = deployment_config.get('rabbit_virtual_host', '/')

    deployment, new = models.get_or_create_deployment(name)

    print "Starting worker for '%s'" % name
    LOG.info("%s: %s %s %s %s" % (name, host, port, user_id, virtual_host))

    params = dict(hostname=host,
                  port=port,
                  userid=user_id,
                  password=password,
                  virtual_host=virtual_host)

    while True:
        with kombu.connection.BrokerConnection(**params) as conn:
            try:
                consumer = NovaConsumer(name, conn, deployment)
                consumer.run()
            except Exception as e:
                LOG.exception("name=%s, exception=%s. Reconnecting in 5s" %
                                (name, e))
                time.sleep(5)

