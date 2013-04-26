# Copyright (c) 2012 - Rackspace Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import json
import unittest

import kombu
import kombu.entity
import kombu.connection
import mox

from stacktach import db, views
import worker.worker as worker


class NovaConsumerTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_get_consumers(self):
        created_queues = []
        created_callbacks =  []
        created_consumers = []
        def Consumer(queues=None, callbacks=None):
            created_queues.extend(queues)
            created_callbacks.extend(callbacks)
            consumer = self.mox.CreateMockAnything()
            created_consumers.append(consumer)
            return consumer
        self.mox.StubOutWithMock(worker.NovaConsumer, '_create_exchange')
        self.mox.StubOutWithMock(worker.NovaConsumer, '_create_queue')
        consumer = worker.NovaConsumer('test', None, None, True, {})
        exchange = self.mox.CreateMockAnything()
        consumer._create_exchange('nova', 'topic').AndReturn(exchange)
        info_queue = self.mox.CreateMockAnything()
        error_queue = self.mox.CreateMockAnything()
        consumer._create_queue('monitor.info', exchange, 'monitor.info')\
                .AndReturn(info_queue)
        consumer._create_queue('monitor.error', exchange, 'monitor.error')\
                .AndReturn(error_queue)
        self.mox.ReplayAll()
        consumers = consumer.get_consumers(Consumer, None)
        self.assertEqual(len(consumers), 1)
        self.assertEqual(consumers[0], created_consumers[0])
        self.assertEqual(len(created_queues), 2)
        self.assertTrue(info_queue in created_queues)
        self.assertTrue(error_queue in created_queues)
        self.assertEqual(len(created_callbacks), 1)
        self.assertTrue(consumer.on_nova in created_callbacks)
        self.mox.VerifyAll()

    def test_create_exchange(self):
        args = {'key': 'value'}
        consumer = worker.NovaConsumer('test', None, None, True, args)

        self.mox.StubOutClassWithMocks(kombu.entity, 'Exchange')
        exchange = kombu.entity.Exchange('nova', type='topic', exclusive=False,
                                         durable=True, auto_delete=False)
        self.mox.ReplayAll()
        actual_exchange = consumer._create_exchange('nova', 'topic')
        self.assertEqual(actual_exchange, exchange)
        self.mox.VerifyAll()

    def test_create_queue(self):
        self.mox.StubOutClassWithMocks(kombu, 'Queue')
        exchange = self.mox.CreateMockAnything()
        queue = kombu.Queue('name', exchange, auto_delete=False, durable=True,
                            exclusive=False, routing_key='routing.key',
                            queue_arguments={})
        consumer = worker.NovaConsumer('test', None, None, True, {})
        self.mox.ReplayAll()
        actual_queue = consumer._create_queue('name', exchange, 'routing.key',
                                              exclusive=False,
                                              auto_delete=False)
        self.assertEqual(actual_queue, queue)
        self.mox.VerifyAll()


    def test_create_queue_with_queue_args(self):
        self.mox.StubOutClassWithMocks(kombu, 'Queue')
        exchange = self.mox.CreateMockAnything()
        queue_args = {'key': 'value'}
        queue = kombu.Queue('name', exchange, auto_delete=False, durable=True,
                            exclusive=False, routing_key='routing.key',
                            queue_arguments=queue_args)
        consumer = worker.NovaConsumer('test', None, None, True, queue_args)
        self.mox.ReplayAll()
        actual_queue = consumer._create_queue('name', exchange, 'routing.key',
                                              exclusive=False,
                                              auto_delete=False)
        self.assertEqual(actual_queue, queue)
        self.mox.VerifyAll()

    def test_process(self):
        deployment = self.mox.CreateMockAnything()
        raw = self.mox.CreateMockAnything()
        message = self.mox.CreateMockAnything()

        consumer = worker.NovaConsumer('test', None, deployment, True, {})
        routing_key = 'monitor.info'
        message.delivery_info = {'routing_key': routing_key}
        body_dict = {u'key': u'value'}
        message.body = json.dumps(body_dict)
        self.mox.StubOutWithMock(views, 'process_raw_data',
                                 use_mock_anything=True)
        args = (routing_key, body_dict)
        views.process_raw_data(deployment, args, json.dumps(args))\
             .AndReturn(raw)
        message.ack()
        self.mox.StubOutWithMock(consumer, '_check_memory',
                                 use_mock_anything=True)
        consumer._check_memory()
        self.mox.ReplayAll()
        consumer._process(message)
        self.assertEqual(consumer.processed, 1)
        self.mox.VerifyAll()

    def test_process_no_raw_dont_ack(self):
        deployment = self.mox.CreateMockAnything()
        raw = self.mox.CreateMockAnything()
        message = self.mox.CreateMockAnything()

        consumer = worker.NovaConsumer('test', None, deployment, True, {})
        routing_key = 'monitor.info'
        message.delivery_info = {'routing_key': routing_key}
        body_dict = {u'key': u'value'}
        message.body = json.dumps(body_dict)
        self.mox.StubOutWithMock(views, 'process_raw_data',
                                 use_mock_anything=True)
        args = (routing_key, body_dict)
        views.process_raw_data(deployment, args, json.dumps(args))\
             .AndReturn(None)
        self.mox.StubOutWithMock(consumer, '_check_memory',
                                 use_mock_anything=True)
        consumer._check_memory()
        self.mox.ReplayAll()
        consumer._process(message)
        self.assertEqual(consumer.processed, 0)
        self.mox.VerifyAll()

    def test_run(self):
        config = {
            'name': 'east_coast.prod.global',
            'durable_queue': False,
            'rabbit_host': '10.0.0.1',
            'rabbit_port': 5672,
            'rabbit_userid': 'rabbit',
            'rabbit_password': 'rabbit',
            'rabbit_virtual_host': '/'
        }
        self.mox.StubOutWithMock(db, 'get_or_create_deployment')
        deployment = self.mox.CreateMockAnything()
        db.get_or_create_deployment(config['name'])\
          .AndReturn((deployment, True))
        self.mox.StubOutWithMock(kombu.connection, 'BrokerConnection')
        params = dict(hostname=config['rabbit_host'],
                      port=config['rabbit_port'],
                      userid=config['rabbit_userid'],
                      password=config['rabbit_password'],
                      transport="librabbitmq",
                      virtual_host=config['rabbit_virtual_host'])
        self.mox.StubOutWithMock(worker, "continue_running")
        worker.continue_running().AndReturn(True)
        conn = self.mox.CreateMockAnything()
        kombu.connection.BrokerConnection(**params).AndReturn(conn)
        conn.__enter__().AndReturn(conn)
        conn.__exit__(None, None, None).AndReturn(None)
        self.mox.StubOutClassWithMocks(worker, 'NovaConsumer')
        consumer = worker.NovaConsumer(config['name'], conn, deployment,
                                       config['durable_queue'], {})
        consumer.run()
        worker.continue_running().AndReturn(False)
        self.mox.ReplayAll()
        worker.run(config)
        self.mox.VerifyAll()

    def test_run_queue_args(self):
        config = {
            'name': 'east_coast.prod.global',
            'durable_queue': False,
            'rabbit_host': '10.0.0.1',
            'rabbit_port': 5672,
            'rabbit_userid': 'rabbit',
            'rabbit_password': 'rabbit',
            'rabbit_virtual_host': '/',
            'queue_arguments': {'x-ha-policy': 'all'}
        }
        self.mox.StubOutWithMock(db, 'get_or_create_deployment')
        deployment = self.mox.CreateMockAnything()
        db.get_or_create_deployment(config['name'])\
          .AndReturn((deployment, True))
        self.mox.StubOutWithMock(kombu.connection, 'BrokerConnection')
        params = dict(hostname=config['rabbit_host'],
                      port=config['rabbit_port'],
                      userid=config['rabbit_userid'],
                      password=config['rabbit_password'],
                      transport="librabbitmq",
                      virtual_host=config['rabbit_virtual_host'])
        self.mox.StubOutWithMock(worker, "continue_running")
        worker.continue_running().AndReturn(True)
        conn = self.mox.CreateMockAnything()
        kombu.connection.BrokerConnection(**params).AndReturn(conn)
        conn.__enter__().AndReturn(conn)
        conn.__exit__(None, None, None).AndReturn(None)
        self.mox.StubOutClassWithMocks(worker, 'NovaConsumer')
        consumer = worker.NovaConsumer(config['name'], conn, deployment,
                                       config['durable_queue'],
                                       config['queue_arguments'])
        consumer.run()
        worker.continue_running().AndReturn(False)
        self.mox.ReplayAll()
        worker.run(config)
        self.mox.VerifyAll()