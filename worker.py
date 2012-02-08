import kombu
import kombu.connection
import kombu.entity
import kombu.mixins


# For now we'll just grab all the fanout messages from compute to scheduler ...
scheduler_exchange = kombu.entity.Exchange("scheduler_fanout", type="fanout",
                                      durable=False, auto_delete=True,
                                      exclusive=True)

nova_exchange = kombu.entity.Exchange("nova", type="topic",
                                      durable=False, auto_delete=False,
                                      exclusive=False)

task_queues = [
        kombu.Queue("scheduler", scheduler_exchange, durable=False, auto_delete=False),
        kombu.Queue("monitor.info", nova_exchange, durable=False, auto_delete=False,
                    exclusive=False, routing_key='monitor.info'),
        kombu.Queue("monitor.error", nova_exchange, durable=False, auto_delete=False,
                    exclusive=False, routing_key='monitor.error'),
    ]

RABBIT_HOST = "localhost"
RABBIT_PORT = 5672
RABBIT_USERID = "guest"
RABBIT_PASSWORD = "guest"
RABBIT_VIRTUAL_HOST = "/"


class SchedulerFanoutConsumer(kombu.mixins.ConsumerMixin):
    def __init__(self, connection):
        self.connection = connection
        self.hosts = {}
        self.request_id = {}
        self.timeline = []

        self.handlers = {'scheduler_fanout':self.on_scheduler,
                         'nova':self.on_nova}

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=task_queues,
                callbacks=[self.on_task])]

    def on_scheduler(self, body, message, routing_key, request_id):
        method = body['method']
        args = body['args']
        host = args['host']
        print "on_scheduler(%s)" % routing_key, method, host
        message.ack()

    def on_nova(self, body, message, routing_key, request_id):
        print "on_nova(%s)" % routing_key,
        if routing_key.startswith("monitor"):
            event_type = body['event_type']
            publisher = body['publisher_id']
            payload = body['payload']
            instance_id = payload['instance_id']
            state = payload['state']
            print event_type, publisher, state, instance_id
            message.ack()
        elif routing_key.startswith("scheduler"):
            spec = body['args']['request_spec']
            image = spec['image']['id']
            flavor = spec['instance_type']['name']
            name = spec['instance_properties']['display_name']
            print name, flavor, image, request_id
            message.requeue()
        else:
            print "Unknown"

    def on_task(self, body, message):
        exchange = message.delivery_info['exchange']
        routing_key = message.delivery_info['routing_key']
        request_id = body['_context_request_id']

        self.handlers[exchange](body, message, routing_key, request_id)


if __name__ == "__main__":
     params = dict(hostname=RABBIT_HOST,
                   port=RABBIT_PORT,
                   userid=RABBIT_USERID,
                   password=RABBIT_PASSWORD,
                   virtual_host=RABBIT_VIRTUAL_HOST)

     with kombu.connection.BrokerConnection(**params) as conn:
         try:
             SchedulerFanoutConsumer(conn).run()
         except KeyboardInterrupt:
             print("bye bye")
