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
import json

import kombu
import mox

from stacktach import db, stacklog
from stacktach import views
import worker.worker as worker
from tests.unit import StacktachBaseTestCase


class ConsumerTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def _setup_mock_logger(self):
        mock_logger = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(stacklog, 'get_logger')
        stacklog.get_logger('worker', is_parent=False).AndReturn(mock_logger)
        return mock_logger

    def _test_topics(self):
        return [
            dict(queue="queue1", routing_key="monitor.info"),
            dict(queue="queue2", routing_key="monitor.error")
        ]

    def test_get_consumers(self):
        created_queues = []
        created_callbacks = []
        created_consumers = []
        def Consumer(queues=None, callbacks=None):
            created_queues.extend(queues)
            created_callbacks.extend(callbacks)
            consumer = self.mox.CreateMockAnything()
            created_consumers.append(consumer)
            return consumer
        self.mox.StubOutWithMock(worker.Consumer, '_create_exchange')
        self.mox.StubOutWithMock(worker.Consumer, '_create_queue')
        consumer = worker.Consumer('test', None, None, True, {}, "nova",
                                   self._test_topics())
        exchange = self.mox.CreateMockAnything()
        consumer._create_exchange('nova', 'topic').AndReturn(exchange)
        info_queue = self.mox.CreateMockAnything()
        error_queue = self.mox.CreateMockAnything()
        consumer._create_queue('queue1', exchange, 'monitor.info')\
                .AndReturn(info_queue)
        consumer._create_queue('queue2', exchange, 'monitor.error')\
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
        consumer = worker.Consumer('test', None, None, True, args, 'nova',
                                   self._test_topics())

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
        consumer = worker.Consumer('test', None, None, True, {}, 'nova',
                                   self._test_topics())
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
        consumer = worker.Consumer('test', None, None, True, queue_args,
                                   'nova', self._test_topics())
        self.mox.ReplayAll()
        actual_queue = consumer._create_queue('name', exchange, 'routing.key',
                                              exclusive=False,
                                              auto_delete=False)
        self.assertEqual(actual_queue, queue)
        self.mox.VerifyAll()

    def test_process(self):
        deployment = self.mox.CreateMockAnything()
        raw = self.mox.CreateMockAnything()
        raw.get_name().AndReturn('RawData')
        message = self.mox.CreateMockAnything()

        exchange = 'nova'
        consumer = worker.Consumer('test', None, deployment, True, {},
                                   exchange, self._test_topics())
        routing_key = 'monitor.info'
        message.delivery_info = {'routing_key': routing_key}
        body_dict = {u'key': u'value'}
        message.body = json.dumps(body_dict)

        mock_notification = self.mox.CreateMockAnything()
        mock_post_process_method = self.mox.CreateMockAnything()
        mock_post_process_method(raw, mock_notification)
        old_handler = worker.POST_PROCESS_METHODS
        worker.POST_PROCESS_METHODS["RawData"] = mock_post_process_method

        self.mox.StubOutWithMock(views, 'process_raw_data',
                                 use_mock_anything=True)
        args = (routing_key, body_dict)
        views.process_raw_data(deployment, args, json.dumps(args), exchange) \
            .AndReturn((raw, mock_notification))
        message.ack()

        self.mox.StubOutWithMock(consumer, '_check_memory',
                                 use_mock_anything=True)
        consumer._check_memory()
        self.mox.ReplayAll()
        consumer._process(message)
        self.assertEqual(consumer.processed, 1)
        self.mox.VerifyAll()
        worker.POST_PROCESS_METHODS["RawData"] = old_handler

    def test_run(self):
        mock_logger = self._setup_mock_logger()
        self.mox.StubOutWithMock(mock_logger, 'info')
        mock_logger.info('east_coast.prod.global: nova 10.0.0.1 5672 rabbit /')
        self.mox.StubOutWithMock(mock_logger, 'debug')
        mock_logger.debug("Processing on 'east_coast.prod.global nova'")
        mock_logger.debug("Completed processing on "
                          "'east_coast.prod.global nova'")
        mock_logger.info("Worker exiting.")

        config = {
            'name': 'east_coast.prod.global',
            'durable_queue': False,
            'rabbit_host': '10.0.0.1',
            'rabbit_port': 5672,
            'rabbit_userid': 'rabbit',
            'rabbit_password': 'rabbit',
            'rabbit_virtual_host': '/',
            "services": ["nova"],
            "topics": {"nova": self._test_topics()}
        }
        self.mox.StubOutWithMock(db, 'get_deployment')
        deployment = self.mox.CreateMockAnything()
        deployment.id = 1
        db.get_deployment(deployment.id).AndReturn(deployment)
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
        self.mox.StubOutClassWithMocks(worker, 'Consumer')
        exchange = 'nova'
        consumer = worker.Consumer(config['name'], conn, deployment,
                                   config['durable_queue'], {}, exchange,
                                   self._test_topics())
        consumer.run()
        worker.continue_running().AndReturn(False)
        self.mox.ReplayAll()
        worker.run(config, deployment.id, exchange)
        self.mox.VerifyAll()

    def test_run_queue_args(self):
        mock_logger = self._setup_mock_logger()
        self.mox.StubOutWithMock(mock_logger, 'info')
        mock_logger.info("east_coast.prod.global: nova 10.0.0.1 5672 rabbit /")
        self.mox.StubOutWithMock(mock_logger, 'debug')
        mock_logger.debug("Processing on 'east_coast.prod.global nova'")
        mock_logger.debug("Completed processing on "
                          "'east_coast.prod.global nova'")
        mock_logger.info("Worker exiting.")

        config = {
            'name': 'east_coast.prod.global',
            'durable_queue': False,
            'rabbit_host': '10.0.0.1',
            'rabbit_port': 5672,
            'rabbit_userid': 'rabbit',
            'rabbit_password': 'rabbit',
            'rabbit_virtual_host': '/',
            'queue_arguments': {'x-ha-policy': 'all'},
            'queue_name_prefix': "test_name_",
            "services": ["nova"],
            "topics": {"nova": self._test_topics()}
        }
        self.mox.StubOutWithMock(db, 'get_deployment')
        deployment = self.mox.CreateMockAnything()
        deployment.id = 1
        db.get_deployment(deployment.id).AndReturn(deployment)
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
        self.mox.StubOutClassWithMocks(worker, 'Consumer')
        exchange = 'nova'
        consumer = worker.Consumer(config['name'], conn, deployment,
                                   config['durable_queue'],
                                   config['queue_arguments'], exchange,
                                   self._test_topics())
        consumer.run()
        worker.continue_running().AndReturn(False)
        self.mox.ReplayAll()
        worker.run(config, deployment.id, exchange)
        self.mox.VerifyAll()
