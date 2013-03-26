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

import argparse
import datetime
import json
import logging
import os
import sys
from time import sleep
import uuid

from django.db import transaction
import kombu.common
import kombu.entity
import kombu.pools
import multiprocessing

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from stacktach import models
from stacktach import datetime_to_decimal as dt
from verifier import AmbiguousResults
from verifier import FieldMismatch
from verifier import NotFound
from verifier import VerificationException

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
handler = logging.handlers.TimedRotatingFileHandler('verifier.log',
                                        when='h', interval=6, backupCount=4)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
LOG.addHandler(handler)


def _list_exists(received_max=None, received_min=None, status=None):
    params = {}
    if received_max:
        params['raw__when__lte'] = dt.dt_to_decimal(received_max)
    if received_min:
        params['raw__when__gt'] = dt.dt_to_decimal(received_min)
    if status:
        params['status'] = status
    return models.InstanceExists.objects.select_related()\
                                .filter(**params).order_by('id')


def _find_launch(instance, launched):
    start = launched - datetime.timedelta(microseconds=launched.microsecond)
    end = start + datetime.timedelta(microseconds=999999)
    params = {'instance': instance,
              'launched_at__gte': dt.dt_to_decimal(start),
              'launched_at__lte': dt.dt_to_decimal(end)}
    return models.InstanceUsage.objects.filter(**params)


def _find_delete(instance, launched, deleted_max=None):
    start = launched - datetime.timedelta(microseconds=launched.microsecond)
    end = start + datetime.timedelta(microseconds=999999)
    params = {'instance': instance,
              'launched_at__gte': dt.dt_to_decimal(start),
              'launched_at__lte': dt.dt_to_decimal(end)}
    if deleted_max:
        params['deleted_at__lte'] = dt.dt_to_decimal(deleted_max)
    return models.InstanceDeletes.objects.filter(**params)


def _mark_exist_verified(exist):
    exist.status = models.InstanceExists.VERIFIED
    exist.save()


def _mark_exist_failed(exist, reason=None):
    exist.status = models.InstanceExists.FAILED
    if reason:
        exist.fail_reason = reason
    exist.save()


def _has_field(d1, d2, field1, field2=None):
    if not field2:
        field2 = field1

    return d1.get(field1) is not None and d2.get(field2) is not None


def _verify_simple_field(d1, d2, field1, field2=None):
    if not field2:
        field2 = field1

    if not _has_field(d1, d2, field1, field2):
        return False
    else:
        if d1[field1] != d2[field2]:
            return False

    return True


def _verify_date_field(d1, d2, same_second=False):
    if d1 and d2:
        if d1 == d2:
            return True
        elif same_second and int(d1) == int(d2):
            return True
    return False


def _verify_for_launch(exist):
    if exist.usage:
        launch = exist.usage
    else:
        if models.InstanceUsage.objects\
                 .filter(instance=exist.instance).count() > 0:
            launches = _find_launch(exist.instance,
                                    dt.dt_from_decimal(exist.launched_at))
            count = launches.count()
            query = {
                'instance': exist.instance,
                'launched_at': exist.launched_at
            }
            if count > 1:
                raise AmbiguousResults('InstanceUsage', query)
            elif count == 0:
                raise NotFound('InstanceUsage', query)
            launch = launches[0]
        else:
            raise NotFound('InstanceUsage', {'instance': exist.instance})

    if not _verify_date_field(launch.launched_at, exist.launched_at,
                              same_second=True):
        raise FieldMismatch('launched_at', exist.launched_at,
                            launch.launched_at)

    if launch.instance_type_id != exist.instance_type_id:
        raise FieldMismatch('instance_type_id', exist.instance_type_id,
                            launch.instance_type_id)


def _verify_for_delete(exist):

    delete = None
    if exist.delete:
        # We know we have a delete and we have it's id
        delete = exist.delete
    else:
        if exist.deleted_at:
            # We received this exists before the delete, go find it
            deletes = _find_delete(exist.instance,
                                   dt.dt_from_decimal(exist.launched_at))
            if deletes.count() == 1:
                delete = deletes[0]
            else:
                query = {
                    'instance': exist.instance,
                    'launched_at': exist.launched_at
                }
                raise NotFound('InstanceDelete', query)
        else:
            # We don't know if this is supposed to have a delete or not.
            # Thus, we need to check if we have a delete for this instance.
            # We need to be careful though, since we could be verifying an
            # exist event that we got before the delete. So, we restrict the
            # search to only deletes before the time this exist was sent.
            # If we find any, we fail validation
            deletes = _find_delete(exist.instance,
                                   dt.dt_from_decimal(exist.launched_at),
                                   dt.dt_from_decimal(exist.raw.when))
            if deletes.count() > 0:
                reason = 'Found InstanceDeletes for non-delete exist'
                raise VerificationException(reason)

    if delete:
        if not _verify_date_field(delete.launched_at, exist.launched_at,
                                  same_second=True):
            raise FieldMismatch('launched_at', exist.launched_at,
                                delete.launched_at)

        if not _verify_date_field(delete.deleted_at, exist.deleted_at,
                                  same_second=True):
            raise FieldMismatch('deleted_at', exist.deleted_at,
                                delete.deleted_at)


def _verify(exist):
    verified = False
    try:
        if not exist.launched_at:
            raise VerificationException("Exists without a launched_at")

        _verify_for_launch(exist)
        _verify_for_delete(exist)

        verified = True
        _mark_exist_verified(exist)
    except VerificationException, e:
        _mark_exist_failed(exist, reason=str(e))
    except Exception, e:
        _mark_exist_failed(exist, reason=e.__class__.__name__)
        LOG.exception(e)

    return verified, exist


results = []


def verify_for_range(pool, when_max, callback=None):
    exists = _list_exists(received_max=when_max,
                          status=models.InstanceExists.PENDING)
    count = exists.count()
    added = 0
    update_interval = datetime.timedelta(seconds=30)
    next_update = datetime.datetime.utcnow() + update_interval
    LOG.info("Adding %s exists to queue." % count)
    while added < count:
        for exist in exists[0:1000]:
            exist.status = models.InstanceExists.VERIFYING
            exist.save()
            result = pool.apply_async(_verify, args=(exist,),
                                      callback=callback)
            results.append(result)
            added += 1
            if datetime.datetime.utcnow() > next_update:
                LOG.info("Added %s exists to queue." % added)
                next_update = datetime.datetime.utcnow() + update_interval

    return count


def clean_results():
    global results

    pending = []
    finished = 0
    successful = 0

    for result in results:
        if result.ready():
            finished += 1
            if result.successful():
                successful += 1
        else:
            pending.append(result)

    results = pending
    errored = finished - successful
    return len(results), successful, errored


def _send_notification(message, routing_key, connection, exchange):
    with kombu.pools.producers[connection].acquire(block=True) as producer:
        kombu.common.maybe_declare(exchange, producer.channel)
        producer.publish(message, routing_key)


def send_verified_notification(exist, connection, exchange, routing_keys=None):
    body = exist.raw.json
    json_body = json.loads(body)
    json_body[1]['event_type'] = 'compute.instance.exists.verified.old'
    json_body[1]['original_message_id'] = json_body[1]['message_id']
    json_body[1]['message_id'] = str(uuid.uuid4())
    if routing_keys is None:
        _send_notification(json_body[1], json_body[0], connection, exchange)
    else:
        for key in routing_keys:
            _send_notification(json_body[1], key, connection, exchange)


def _create_exchange(name, type, exclusive=False, auto_delete=False,
                     durable=True):
    return kombu.entity.Exchange(name, type=type, exclusive=auto_delete,
                                 auto_delete=exclusive, durable=durable)


def _create_connection(config):
    rabbit = config['rabbit']
    conn_params = dict(hostname=rabbit['host'],
                       port=rabbit['port'],
                       userid=rabbit['userid'],
                       password=rabbit['password'],
                       transport="librabbitmq",
                       virtual_host=rabbit['virtual_host'])
    return kombu.connection.BrokerConnection(**conn_params)


def _run(config, pool, callback=None):
    tick_time = config['tick_time']
    settle_units = config['settle_units']
    settle_time = config['settle_time']
    while True:
        with transaction.commit_on_success():
            now = datetime.datetime.utcnow()
            kwargs = {settle_units: settle_time}
            when_max = now - datetime.timedelta(**kwargs)
            new = verify_for_range(pool, when_max, callback=callback)

            msg = "N: %s, P: %s, S: %s, E: %s" % ((new,) + clean_results())
            LOG.info(msg)
        sleep(tick_time)


def run(config):
    pool = multiprocessing.Pool(config['pool_size'])

    if config['enable_notifications']:
        exchange = _create_exchange(config['rabbit']['exchange_name'],
                                    'topic',
                                    durable=config['rabbit']['durable_queue'])
        routing_keys = None
        if config['rabbit'].get('routing_keys') is not None:
            routing_keys = config['rabbit']['routing_keys']

        with _create_connection(config) as conn:
            def callback(result):
                (verified, exist) = result
                if verified:
                    send_verified_notification(exist, conn, exchange,
                                               routing_keys=routing_keys)

            _run(config, pool, callback=callback)
    else:
        _run(config, pool)


def _run_once(config, pool, callback=None):
    tick_time = config['tick_time']
    settle_units = config['settle_units']
    settle_time = config['settle_time']
    now = datetime.datetime.utcnow()
    kwargs = {settle_units: settle_time}
    when_max = now - datetime.timedelta(**kwargs)
    new = verify_for_range(pool, when_max, callback=callback)

    LOG.info("Verifying %s exist events" % new)
    while len(results) > 0:
        LOG.info("P: %s, F: %s, E: %s" % clean_results())
        sleep(tick_time)


def run_once(config):
    pool = multiprocessing.Pool(config['pool_size'])

    if config['enable_notifications']:
        exchange = _create_exchange(config['rabbit']['exchange_name'],
                                    'topic',
                                    durable=config['rabbit']['durable_queue'])
        routing_keys = None
        if config['rabbit'].get('routing_keys') is not None:
            routing_keys = config['rabbit']['routing_keys']

        with _create_connection(config) as conn:
            def callback(result):
                (verified, exist) = result
                if verified:
                    send_verified_notification(exist, conn, exchange,
                                               routing_keys=routing_keys)

            _run_once(config, pool, callback=callback)
    else:
        _run_once(config, pool)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=
                                     "Stacktach Instance Exists Verifier")
    parser.add_argument('--tick-time',
                        help='Time in seconds the verifier will sleep before'
                             'it will check for new exists records.',
                        default=30)
    parser.add_argument('--run-once',
                        help='Check database once and verify all returned'
                             'exists records, then stop',
                        type=bool,
                        default=False)
    parser.add_argument('--settle-time',
                        help='Time the verifier will wait for records to'
                             'settle before it will verify them.',
                        default=10)
    parser.add_argument('--settle-units',
                        help='Units for settle time',
                        default='minutes')
    parser.add_argument('--pool-size',
                        help='Number of processes created to verify records',
                        type=int,
                        default=10)
    args = parser.parse_args()
    config = {'tick_time': args.tick_time, 'settle_time': args.settle_time,
              'settle_units': args.settle_units, 'pool_size': args.pool_size}

    if args.run_once:
        run_once(config)
    else:
        run(config)
