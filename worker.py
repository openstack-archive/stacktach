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
#        kombu.Queue("scheduler", scheduler_exchange, durable=False, auto_delete=False),
        kombu.Queue("monitor.info", nova_exchange, durable=False, auto_delete=False),
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
        return [Consumer(queues=task_queues,
                callbacks=[self.on_task])]

    def on_task(self, body, message):
        message.ack()


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
