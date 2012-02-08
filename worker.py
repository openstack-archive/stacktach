import kombu
import kombu.connection
import kombu.entity
import kombu.mixins
import pprint
import readline
import rlcompleter
import threading
import time


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
        self.hosts = {}
        self.timeline = []
        self.instances = {}
        self.lock = threading.Lock()

    def get_status(self):
        with self.lock:
            return "%s/%s" % (len(self.hosts), len(self.instances))

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=scheduler_queues, callbacks=[self.on_scheduler]),
                Consumer(queues=nova_queues, callbacks=[self.on_nova])]

    def _process(self, body, message, host=None, instance_id=None):
            routing_key = message.delivery_info['routing_key']

            payload = (routing_key, body)

            self.timeline.append(payload)

            if host:
                host_rec = self.hosts.get(host, [])
                host_rec.append(payload)
                self.hosts[host] = host_rec

            if instance_id:
                instance_rec = self.instances.get(instance_id, [])
                instance_rec.append(payload)
                self.instances[instance_id]=instance_rec

    def get_host(self, host):
        # There is still a lock issue here since we're returning
        # a list which could get modified in this thread.
        with self.lock:
            return self.hosts.get(host)

    def get_instance(self, instance):
        # See warning above.
        with self.lock:
            return self.instances.get(instance)

    def on_scheduler(self, body, message):
        with self.lock:
            method = body['method']
            args = body['args']
            if 'host' not in args:
                print "SCHEDULER? ", body
            else:
                host = args['host']
                print "on_scheduler(%s)" % routing_key, method, host
            message.ack()

    def on_nova(self, body, message):
        with self.lock:
            # print "on_nova(%s)" % routing_key,
            event_type = body['event_type']
            publisher = body['publisher_id']
            host = publisher.split('.')[1]
            payload = body['payload']
            instance_id = payload.get('instance_id',
                                      payload.get('instance_uuid', None))
            state = payload.get('state', '<unknown state>')
            print event_type, publisher, state, instance_id
            message.ack()

            self._process(body, message, host=host, instance_id=instance_id)


class Monitor(threading.Thread):
    def run(self):
        params = dict(hostname=RABBIT_HOST,
                       port=RABBIT_PORT,
                       userid=RABBIT_USERID,
                       password=RABBIT_PASSWORD,
                       virtual_host=RABBIT_VIRTUAL_HOST)

        with kombu.connection.BrokerConnection(**params) as conn:
             self.consumer = SchedulerFanoutConsumer(conn)
             try:
                 self.consumer.run()
             except KeyboardInterrupt:
                 print("bye bye")


if __name__ == "__main__":
    monitor = Monitor()
    monitor.start()
    time.sleep(5)  #hack
    consumer = monitor.consumer
    pp = pprint.PrettyPrinter(indent=2)

    readline.parse_and_bind('tab: complete')
    more = True
    while more:
        print "%s>" % consumer.get_status(),
        line = raw_input()
        parts = line.split(' ')

        if line == 'quit':
            more = False

        result = None
        if parts[0]=='i':
            result = consumer.get_instance(parts[1])

        if parts[0]=='h':
            result = consumer.get_host(parts[1])

        if result:
            pp.pprint(result)
