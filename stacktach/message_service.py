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
        hostname=hostname, port=port, userid=userid, password=password,
        transport=transport, virtual_host=virtual_host)


def create_queue(name, exchange, routing_key, exclusive=False,
                 auto_delete=False, queue_arguments=None, durable=True):
    return kombu.Queue(name, exchange, durable=durable,
                       auto_delete=auto_delete, exclusive=exclusive,
                       queue_arguments=queue_arguments,
                       routing_key=routing_key)
