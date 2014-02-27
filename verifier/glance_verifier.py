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
import json

import os
import sys
import uuid
from verifier.base_verifier import Verifier


POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from stacktach import models
from verifier import FieldMismatch
from verifier import VerificationException
from verifier import base_verifier
from verifier import NullFieldException
from verifier import NotFound
from stacktach import datetime_to_decimal as dt
from stacktach import stacklog
from stacktach import message_service
import datetime

stacklog.set_default_logger_name('verifier')


def _get_child_logger():
    return stacklog.get_logger('verifier', is_parent=False)


def _verify_field_mismatch(exists, usage):
    if not base_verifier._verify_date_field(
            usage.created_at, exists.created_at, same_second=True):
        raise FieldMismatch(
            'created_at',
            {'name': 'exists', 'value': exists.created_at},
            {'name': 'launches', 'value': usage.created_at},
            exists.uuid)

    if usage.owner != exists.owner:
        raise FieldMismatch(
            'owner',
            {'name': 'exists', 'value': exists.owner},
            {'name': 'launches', 'value': usage.owner},
            exists.uuid)

    if usage.size != exists.size:
        raise FieldMismatch(
            'size',
            {'name': 'exists', 'value': exists.size},
            {'name': 'launches', 'value': usage.size},
            exists.uuid)


def _verify_validity(exist):
    fields = {exist.size: 'image_size', exist.created_at: 'created_at',
              exist.uuid: 'uuid', exist.owner: 'owner'}
    for (field_value, field_name) in fields.items():
        if field_value is None:
            raise NullFieldException(field_name, exist.id, exist.uuid)
    base_verifier._is_like_uuid('uuid', exist.uuid, exist.id)
    base_verifier._is_like_date('created_at', exist.created_at, exist.id,
                                exist.uuid)
    base_verifier._is_long('size', exist.size, exist.id, exist.uuid)
    base_verifier._is_hex_owner_id('owner', exist.owner, exist.id, exist.uuid)


def _verify_for_usage(exist, usage=None):
    usage_type = "ImageUsage"
    if not usage and exist.usage:
        usage = exist.usage
    elif not usage:
        usages = models.ImageUsage.objects.filter(uuid=exist.uuid)
        usage_count = usages.count()
        if usage_count == 0:
            query = {'uuid': exist.uuid}
            raise NotFound(usage_type, query)
        usage = usages[0]
    _verify_field_mismatch(exist, usage)


def _verify_for_delete(exist, delete=None):
    delete_type = "ImageDelete"
    if not delete and exist.delete:
        # We know we have a delete and we have it's id
        delete = exist.delete
    elif not delete:
        if exist.deleted_at:
            # We received this exists before the delete, go find it
            deletes = models.ImageDeletes.find(uuid=exist.uuid)
            if deletes.count() == 1:
                delete = deletes[0]
            else:
                query = {
                    'instance': exist.instance,
                    'launched_at': exist.launched_at
                }
                raise NotFound(delete_type, query)
        else:
            # We don't know if this is supposed to have a delete or not.
            # Thus, we need to check if we have a delete for this instance.
            # We need to be careful though, since we could be verifying an
            # exist event that we got before the delete. So, we restrict the
            # search to only deletes before this exist's audit period ended.
            # If we find any, we fail validation
            deleted_at_max = dt.dt_from_decimal(exist.audit_period_ending)
            deletes = models.ImageDeletes.find(
                exist.uuid, deleted_at_max)
            if deletes.count() > 0:
                reason = 'Found %ss for non-delete exist' % delete_type
                raise VerificationException(reason)

    if delete:
        if not base_verifier._verify_date_field(
                delete.deleted_at, exist.deleted_at, same_second=True):
            raise FieldMismatch(
                'deleted_at',
                {'name': 'exists', 'value': exist.deleted_at},
                {'name': 'deletes', 'value': delete.deleted_at},
                exist.uuid)


def _verify(exists):
    verified = True
    for exist in exists:
        try:
            _verify_for_usage(exist)
            _verify_for_delete(exist)
            _verify_validity(exist)

            exist.mark_verified()
        except VerificationException, e:
            verified = False
            exist.mark_failed(reason=str(e))
        except Exception, e:
            verified = False
            exist.mark_failed(reason=e.__class__.__name__)
            _get_child_logger().exception("glance: %s" % e)

    return verified, exists[0]


class GlanceVerifier(Verifier):
    def __init__(self, config, pool=None):
        super(GlanceVerifier, self).__init__(config, pool=pool)

    def verify_exists(self, grouped_exists, callback, verifying_status):
        count = len(grouped_exists)
        added = 0
        update_interval = datetime.timedelta(seconds=30)
        next_update = datetime.datetime.utcnow() + update_interval
        _get_child_logger().info("glance: Adding %s per-owner exists to queue." % count)
        while added < count:
            for exists in grouped_exists.values():
                for exist in exists:
                    exist.status = verifying_status
                    exist.save()
                result = self.pool.apply_async(_verify, args=(exists,),
                                               callback=callback)
                self.results.append(result)
                added += 1
                if datetime.datetime.utcnow() > next_update:
                    values = ((added,) + self.clean_results())
                    msg = "glance: N: %s, P: %s, S: %s, E: %s" % values
                    _get_child_logger().info(msg)
                    next_update = datetime.datetime.utcnow() + update_interval
        return count

    def verify_for_range(self, ending_max, callback=None):
        unsent_exists_grouped_by_owner_and_rawid = \
            models.ImageExists.find_and_group_by_owner_and_raw_id(
                ending_max=ending_max,
                status=models.ImageExists.SENT_UNVERIFIED)
        unsent_count = self.verify_exists(unsent_exists_grouped_by_owner_and_rawid,
                                        None, models.ImageExists.SENT_VERIFYING)
        exists_grouped_by_owner_and_rawid = \
            models.ImageExists.find_and_group_by_owner_and_raw_id(
                ending_max=ending_max,
                status=models.ImageExists.PENDING)
        count = self.verify_exists(exists_grouped_by_owner_and_rawid, callback,
                                 models.ImageExists.VERIFYING)

        return count+unsent_count

    def send_verified_notification(self, exist, connection, exchange,
                                   routing_keys=None):
        # NOTE (apmelton)
        # The exist we're provided from the callback may have cached queries
        # from before it was serialized. We don't want to use them as
        # they could have been lost somewhere in the process forking.
        # So, grab a new InstanceExists object from the database and use it.
        body = models.ImageExists.objects.get(id=exist.id).raw.json
        json_body = json.loads(body)
        json_body[1]['event_type'] = self.config.glance_event_type()
        json_body[1]['original_message_id'] = json_body[1]['message_id']
        json_body[1]['message_id'] = str(uuid.uuid4())
        if routing_keys is None:
            message_service.send_notification(json_body[1], json_body[0],
                                              connection, exchange)
        else:
            for key in routing_keys:
                message_service.send_notification(json_body[1], key,
                                                  connection, exchange)

    def exchange(self):
        return 'glance'
