# Copyright 2012 - Dark Secret Software Inc.

import json
import kombu
import kombu.connection
import kombu.entity
import kombu.mixins
import threading
import urllib
import urllib2

url = 'http://darksecretsoftware.com/stacktach/data/'

# For now we'll just grab all the fanout messages from compute to scheduler ...
scheduler_exchange = kombu.entity.Exchange("scheduler_fanout", type="fanout",
                                      durable=False, auto_delete=True,
                                      exclusive=True)

scheduler_queues = [
        # The Queue name has to be unique or we we'll end up with Round Robin
        # behavior from Rabbit, even though it's a Fanout queue. In Nova the queues
        # have UUID's tacked on the end.
        kombu.Queue("scheduler.xxx", scheduler_exchange, durable=False, auto_delete=False),
    ]

nova_exchange = kombu.entity.Exchange("nova", type="topic",
                                      durable=False, auto_delete=False,
                                      exclusive=False)

nova_queues = [
        kombu.Queue("monitor", nova_exchange, durable=False, auto_delete=False,
                    exclusive=False, routing_key='monitor.*'),
    ]

RABBIT_HOST = "localhost"
RABBIT_PORT = 5672
RABBIT_USERID = "guest"
RABBIT_PASSWORD = "guest"
RABBIT_VIRTUAL_HOST = "/"


class SchedulerFanoutConsumer(kombu.mixins.ConsumerMixin):
    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=scheduler_queues, callbacks=[self.on_scheduler]),
                Consumer(queues=nova_queues, callbacks=[self.on_nova])]

    def _process(self, body, message):
        routing_key = message.delivery_info['routing_key']
        payload = (routing_key, body)
        jvalues = json.dumps(payload)

        try:
            raw_data = dict(args=jvalues)
            cooked_data = urllib.urlencode(raw_data)
            req = urllib2.Request(url, cooked_data)
            response = urllib2.urlopen(req)
            page = response.read()
            print "sent", page
        except urllib2.HTTPError, e:
            print e
            page = e.read()
            print page
            raise

    def on_scheduler(self, body, message):
        self._process(body, message)
        message.ack()

    def on_nova(self, body, message):
        self._process(body, message)
        message.ack()


if __name__ == "__main__":
    params = dict(hostname=RABBIT_HOST,
                  port=RABBIT_PORT,
                  userid=RABBIT_USERID,
                  password=RABBIT_PASSWORD,
                  virtual_host=RABBIT_VIRTUAL_HOST)

    with kombu.connection.BrokerConnection(**params) as conn:
         consumer = SchedulerFanoutConsumer(conn)
         try:
             consumer.run()
         except KeyboardInterrupt:
             print("bye bye")
