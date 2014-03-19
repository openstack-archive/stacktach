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

import datetime
import sys
import time
import signal

import kombu
import kombu.mixins


try:
    import ujson as json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        import json

from pympler.process import ProcessMemoryInfo

from stacktach import db
from stacktach import message_service
from stacktach import stacklog
from stacktach import views

stacklog.set_default_logger_name('worker')
shutdown_soon = False


def _get_child_logger():
    return stacklog.get_logger('worker', is_parent=False)


class Consumer(kombu.mixins.ConsumerMixin):
    def __init__(self, name, connection, deployment, durable, queue_arguments,
                 exchange, topics):
        self.connection = connection
        self.deployment = deployment
        self.durable = durable
        self.queue_arguments = queue_arguments
        self.name = name
        self.last_time = None
        self.pmi = None
        self.processed = 0
        self.total_processed = 0
        self.topics = topics
        self.exchange = exchange
        signal.signal(signal.SIGTERM, self._shutdown)

    def _create_exchange(self, name, type, exclusive=False, auto_delete=False):
        return message_service.create_exchange(name, exchange_type=type,
                                               exclusive=exclusive,
                                               durable=self.durable,
                                               auto_delete=auto_delete)

    def _create_queue(self, name, nova_exchange, routing_key, exclusive=False,
                     auto_delete=False):
        return message_service.create_queue(
            name, nova_exchange, durable=self.durable, auto_delete=exclusive,
            exclusive=auto_delete, queue_arguments=self.queue_arguments,
            routing_key=routing_key)

    def get_consumers(self, Consumer, channel):
        exchange = self._create_exchange(self.exchange, "topic")

        queues = [self._create_queue(topic['queue'], exchange,
                                     topic['routing_key'])
                  for topic in self.topics]

        return [Consumer(queues=queues, callbacks=[self.on_nova])]

    def _process(self, message):
        routing_key = message.delivery_info['routing_key']

        body = str(message.body)
        args = (routing_key, json.loads(body))
        asJson = json.dumps(args)
        # save raw and ack the message
        raw, notif = views.process_raw_data(
            self.deployment, args, asJson, self.exchange)

        self.processed += 1
        message.ack()
        POST_PROCESS_METHODS[raw.get_name()](raw, notif)

        self._check_memory()

    def _check_memory(self):
        if not self.pmi:
            self.pmi = ProcessMemoryInfo()
            self.last_vsz = self.pmi.vsz
            self.initial_vsz = self.pmi.vsz

        utc = datetime.datetime.utcnow()
        check = self.last_time is None
        if self.last_time:
            diff = utc - self.last_time
            if diff.seconds > 30:
                check = True
        if check:
            self.last_time = utc
            self.pmi.update()
            diff = (self.pmi.vsz - self.last_vsz) / 1000
            idiff = (self.pmi.vsz - self.initial_vsz) / 1000
            self.total_processed += self.processed
            per_message = 0
            if self.total_processed:
                per_message = idiff / self.total_processed
            _get_child_logger().debug("%20s %20s %6dk/%6dk ram, "
                      "%3d/%4d msgs @ %6dk/msg" %
                      (self.name, self.exchange, diff, idiff, self.processed,
                      self.total_processed, per_message))
            self.last_vsz = self.pmi.vsz
            self.processed = 0

    def on_nova(self, body, message):
        try:
            self._process(message)
        except Exception, e:
            _get_child_logger().debug("Problem: %s\nFailed message body:\n%s" %
                      (e, json.loads(str(message.body))))
            raise

    def _shutdown(self, signal, stackframe = False):
        global shutdown_soon
        self.should_stop = True
        shutdown_soon = True

    def on_connection_revived(self):
        _get_child_logger().debug("The connection to RabbitMQ was revived.")

    def on_connection_error(self, exc, interval):
        _get_child_logger().error("RabbitMQ Broker connection error: %r. "
                                  "Trying again in %s seconds.", exc, interval)

    def on_decode_error(self, message, exc):
        _get_child_logger().exception("Decode Error: %s" % exc)
        # do NOT call message.ack(), otherwise the message will be lost


def continue_running():
    return not shutdown_soon


def exit_or_sleep(exit=False):
    if exit:
        sys.exit(1)
    time.sleep(5)


def run(deployment_config, deployment_id, exchange):
    name = deployment_config['name']
    host = deployment_config.get('rabbit_host', 'localhost')
    port = deployment_config.get('rabbit_port', 5672)
    user_id = deployment_config.get('rabbit_userid', 'rabbit')
    password = deployment_config.get('rabbit_password', 'rabbit')
    virtual_host = deployment_config.get('rabbit_virtual_host', '/')
    durable = deployment_config.get('durable_queue', True)
    queue_arguments = deployment_config.get('queue_arguments', {})
    exit_on_exception = deployment_config.get('exit_on_exception', False)
    topics = deployment_config.get('topics', {})
    logger = _get_child_logger()

    deployment = db.get_deployment(deployment_id)

    print "Starting worker for '%s %s'" % (name, exchange)
    logger.info("%s: %s %s %s %s %s" %
                (name, exchange, host, port, user_id, virtual_host))

    params = dict(hostname=host,
                  port=port,
                  userid=user_id,
                  password=password,
                  transport="librabbitmq",
                  virtual_host=virtual_host)

    # continue_running() is used for testing
    while continue_running():
        try:
            logger.debug("Processing on '%s %s'" % (name, exchange))
            with kombu.connection.BrokerConnection(**params) as conn:
                try:
                    consumer = Consumer(name, conn, deployment, durable,
                                        queue_arguments, exchange,
                                        topics[exchange])
                    consumer.run()
                except Exception as e:
                    logger.error("!!!!Exception!!!!")
                    logger.exception(
                        "name=%s, exchange=%s, exception=%s. "
                        "Reconnecting in 5s" % (name, exchange, e))
                    exit_or_sleep(exit_on_exception)
            logger.debug("Completed processing on '%s %s'" %
                                      (name, exchange))
        except Exception:
            logger.error("!!!!Exception!!!!")
            e = sys.exc_info()[0]
            msg = "Uncaught exception: deployment=%s, exchange=%s, " \
                  "exception=%s. Retrying in 5s"
            logger.exception(msg % (name, exchange, e))
            exit_or_sleep(exit_on_exception)
    logger.info("Worker exiting.")

signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGTERM, signal.SIG_IGN)

POST_PROCESS_METHODS = {
    'RawData': views.post_process_rawdata,
    'GlanceRawData': views.post_process_glancerawdata,
    'GenericRawData': views.post_process_genericrawdata
}
