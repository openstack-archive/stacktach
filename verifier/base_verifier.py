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

import datetime
import decimal
import os
import re
import sys
import time
import multiprocessing

from django.db import transaction
from stacktach import message_service


POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from django.db import close_connection
from django.db import reset_queries
from django.core import exceptions

from verifier import WrongTypeException
from stacktach import stacklog

stacklog.set_default_logger_name('verifier')


def _get_child_logger():
    return stacklog.get_logger('verifier', is_parent=False)


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


def _is_like_uuid(attr_name, attr_value, exist_id):
    if not re.match("[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$",
             attr_value):
        raise WrongTypeException(attr_name, attr_value, exist_id, None)


def _is_like_date(attr_name, attr_value, exist_id, instance_uuid):
    if not isinstance(attr_value, decimal.Decimal):
        raise WrongTypeException(attr_name, attr_value, exist_id, instance_uuid)


def _is_long(attr_name, attr_value, exist_id, instance_uuid):
    if not isinstance(attr_value, long):
        raise WrongTypeException(attr_name, attr_value, exist_id, instance_uuid)


def _is_int_in_char(attr_name, attr_value, exist_id, instance_uuid):
    try:
        int(attr_value)
    except ValueError:
        raise WrongTypeException(attr_name, attr_value, exist_id, instance_uuid)


def _is_hex_owner_id(attr_name, attr_value, exist_id, instance_uuid):
    if not re.match("^[0-9a-fA-F]+$", attr_value):
        raise WrongTypeException(attr_name, attr_value, exist_id, instance_uuid)


def _is_alphanumeric(attr_name, attr_value, exist_id, instance_uuid):
    if not re.match("[a-zA-Z0-9.]+$", attr_value):
        raise WrongTypeException(attr_name, attr_value, exist_id, instance_uuid)


class Verifier(object):
    def __init__(self, config, pool=None, reconciler=None):
        self.config = config
        self.pool = pool or multiprocessing.Pool(config.pool_size())
        self.enable_notifications = config.enable_notifications()
        self.reconciler = reconciler
        self.results = []
        self.failed = []

    def clean_results(self):
        pending = []
        finished = 0
        successful = 0

        for result in self.results:
            if result.ready():
                finished += 1
                if result.successful():
                    (verified, exists) = result.get()
                    if self.reconciler and not verified:
                        self.failed.append(exists)
                    successful += 1
            else:
                pending.append(result)

        self.results = pending
        errored = finished - successful
        return len(self.results), successful, errored

    def _keep_running(self):
        return True

    def _utcnow(self):
        return datetime.datetime.utcnow()

    def _run(self, callback=None):
        tick_time = self.config.tick_time()
        settle_units = self.config.settle_units()
        settle_time = self.config.settle_time()
        while self._keep_running():
            with transaction.commit_on_success():
                now = self._utcnow()
                kwargs = {settle_units: settle_time}
                ending_max = now - datetime.timedelta(**kwargs)
                new = self.verify_for_range(ending_max, callback=callback)
                values = ((self.exchange(), new,) + self.clean_results())
                if self.reconciler:
                    self.reconcile_failed()
                msg = "%s: N: %s, P: %s, S: %s, E: %s" % values
                _get_child_logger().info(msg)
            time.sleep(tick_time)

    def run(self):
        logger = _get_child_logger()
        if self.enable_notifications:
            exchange_name = self.exchange()
            exchange = message_service.create_exchange(
                exchange_name, 'topic',
                durable=self.config.durable_queue())
            routing_keys = self.config.topics()[exchange_name]

            with message_service.create_connection(
                self.config.host(), self.config.port(),
                self.config.userid(), self.config.password(),
                "librabbitmq", self.config.virtual_host()) as conn:
                def callback(result):
                    attempt = 0
                    while attempt < 2:
                        try:
                            (verified, exist) = result
                            if verified:
                                self.send_verified_notification(
                                    exist, conn, exchange,
                                    routing_keys=routing_keys)
                            break
                        except exceptions.ObjectDoesNotExist:
                            if attempt < 1:
                                logger.warn("ObjectDoesNotExist in callback, "
                                         "attempting to reconnect and try "
                                         "again.")
                                close_connection()
                                reset_queries()
                            else:
                                logger.error("ObjectDoesNotExist in callback "
                                          "again, giving up.")
                        except Exception, e:
                            msg = "ERROR in Callback %s: %s" % (exchange_name,
                                                                e)
                            logger.exception(msg)
                            break
                        attempt += 1
                try:
                    self._run(callback=callback)
                except Exception, e:
                    print e
                    raise e
        else:
            self._run()

    def verify_for_range(self, ending_max, callback=None):
        pass

    def reconcile_failed(self):
        pass

    def exchange(self):
        pass
