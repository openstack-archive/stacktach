import unittest

import kombu
import kombu.entity
import mox

import worker.worker as worker

class NovaConsumerTestCase(unittest.TestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def test_get_consumer(self):
        created_queues = None
        created_callback =  None
        created_consumers = []
        def Consumer(queues=None, callbacks=None):
            created_queues = queues
            created_callback = callbacks
            consumer = self.mox.CreateMockAnything()
            created_consumers.append(consumer)
            return consumer
        self.mox.StubOutClassWithMocks(kombu.entity, 'Exchange')
        self.mox.StubOutClassWithMocks(kombu, 'Queue')
        kombu.entity.Exchange('nova', type='topic', exclusive=False,
                              durable=True, auto_delete=False)
        kombu.Queue('monitor.info', kombu.entity.Exchange, auto_delete=False,
                    durable=True, exclusive=False, routing_key='monitor.info')
        kombu.Queue('monitor.error', kombu.entity.Exchange, auto_delete=False,
                    durable=True, exclusive=False, routing_key='monitor.error')
        consumer = worker.NovaConsumer('test', None, None, True)
        self.mox.ReplayAll()
        consumers = consumer.get_consumers(Consumer, None)
        self.assertEqual(len(consumers), len(created_consumers))
        self.assertEqual(consumers[0], created_consumers[0])
        self.mox.VerifyAll()