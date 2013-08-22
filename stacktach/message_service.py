import kombu
import kombu.entity
import kombu.pools
import kombu.connection
import kombu.common

def send_notification(message, routing_key, connection, exchange):
    with kombu.pools.producers[connection].acquire(block=True) as producer:
        kombu.common.maybe_declare(exchange, producer.channel)
        producer.publish(message, routing_key)


def create_exchange(name, exchange_type, exclusive=False, auto_delete=False,
                    durable=True):
    return kombu.entity.Exchange(name, type=exchange_type, exclusive=exclusive,
                                 auto_delete=auto_delete, durable=durable)


def create_connection(hostname, port, userid, password, transport,
                      virtual_host):
    return kombu.connection.BrokerConnection(
        hostname=hostname, port=port, user_id=userid, password=password,
        transport=transport, virtual_host=virtual_host)


def create_queue(name, exchange, routing_key, exclusive=False,
                 auto_delete=False, queue_arguments=None, durable=True):
    return kombu.Queue(name, exchange, durable=durable,
                       auto_delete=auto_delete, exclusive=exclusive,
                       queue_arguments=queue_arguments,
                       routing_key=routing_key)
