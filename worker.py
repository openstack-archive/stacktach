import kombu
import kombu.connection
import kombu.entity
import kombu.mixins

# For now we'll just grab all the fanout messages from compute to scheduler ...
task_exchange = kombu.entity.Exchange("scheduler_fanout", type="fanout",
                                      durable=False, auto_delete=True,
                                      exclusive=True)
task_queues = [kombu.Queue("scheduler", task_exchange, durable=False, auto_delete=False), ]

RABBIT_HOST = "localhost"
RABBIT_PORT = 5672
RABBIT_USERID = "guest"
RABBIT_PASSWORD = "guest"
RABBIT_VIRTUAL_HOST = "/"


class Worker(kombu.mixins.ConsumerMixin):
    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=task_queues,
                callbacks=[self.on_task])]

    def on_task(self, body, message):
        self.info("Got task: %s / %s" % (body, message))
        message.ack()


if __name__ == "__main__":
     from kombu.utils.debug import setup_logging
     setup_logging(loglevel="INFO")

     params = dict(hostname=RABBIT_HOST,
                   port=RABBIT_PORT,
                   userid=RABBIT_USERID,
                   password=RABBIT_PASSWORD,
                   virtual_host=RABBIT_VIRTUAL_HOST)

     with kombu.connection.BrokerConnection(**params) as conn:
         try:
             Worker(conn).run()
         except KeyboardInterrupt:
             print("bye bye")
