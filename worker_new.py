# Copyright 2012 Openstack LLC.
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

import amqplib.client_0_8 as amqp
import json
import socket
import time

from stacktach import models, views


class NovaConsumer(object):
    def __init__(self, channel, tenant_id, logger):
        self.channel = channel
        self.tenant = models.Tenant.objects.get(tenant_id=tenant_id)
        self.logger = logger
        channel.basic_consume('monitor.info', callback=self.onMessage)
        channel.basic_consume('monitor.error', callback=self.onMessage)

    def onMessage(self, message):
        routing_key = message.delivery_info['routing_key']
        args = (routing_key, json.loads(message.body))
        asJson = json.dumps(args)

        #from pprint import pformat
        #self.logger.debug("Saving %s", pformat(args))
        views._parse(self.tenant, args, asJson)
        self.logger.debug("Recorded %s ", routing_key)
        self.channel.basic_ack(message.delivery_tag)


def run(deployment, logger):
    tenant_id = deployment.get('tenant_id', 1)
    host = deployment.get('rabbit_host', 'localhost')
    port = deployment.get('rabbit_port', 5672)
    user_id = deployment.get('rabbit_userid', 'rabbit')
    password = deployment.get('rabbit_password', 'rabbit')
    virtual_host = deployment.get('rabbit_virtual_host', '/')

    logger.info("Rabbit: %s %s %s %s" % 
                            (host, port, user_id, virtual_host))


    while 1:
        try:
            conn = amqp.Connection(host, userid=user_id, password=password, virtual_host=virtual_host)

            ch = conn.channel()
            ch.access_request(virtual_host, active=True, read=True)

            ch.exchange_declare('nova', type='topic', durable=True, auto_delete=False)
            ch.queue_declare('monitor.info', durable=True, auto_delete=False, exclusive=False)
            ch.queue_declare('monitor.error', durable=True, auto_delete=False, exclusive=False)
            ch.queue_bind('monitor.info', 'nova')
            ch.queue_bind('monitor.error', 'nova')
            consumer = NovaConsumer(ch, tenant_id, logger)
            #
            # Loop as long as the channel has callbacks registered
            #
            while ch.callbacks:
                ch.wait()
            break
        except socket.error, e:
            logger.warn("Socket error: %s" % e)
            time.sleep(5)
            continue

    ch.close()
    conn.close()
    logger.info("Finished")
