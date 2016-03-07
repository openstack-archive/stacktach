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
import datetime
import json
import os
import sys
import uuid


POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from verifier import base_verifier
from verifier import config
from verifier import NullFieldException
from stacktach import models
from stacktach import stacklog
from stacktach import datetime_to_decimal as dt
from verifier import FieldMismatch
from verifier import AmbiguousResults
from verifier import NotFound
from verifier import VerificationException
from stacktach import message_service

stacklog.set_default_logger_name('verifier')


def _get_child_logger():
    return stacklog.get_logger('verifier', is_parent=False)


def _verify_field_mismatch(exists, launch):
    flavor_field_name = config.flavor_field_name()
    if not base_verifier._verify_date_field(
            launch.launched_at, exists.launched_at, same_second=True):
        raise FieldMismatch(
            'launched_at',
            {'name': 'exists', 'value': exists.launched_at},
            {'name': 'launches', 'value': launch.launched_at},
            exists.instance)

    if getattr(launch, flavor_field_name) != \
            getattr(exists, flavor_field_name):
        raise FieldMismatch(
            flavor_field_name,
            {'name': 'exists', 'value': getattr(exists, flavor_field_name)},
            {'name': 'launches', 'value': getattr(launch, flavor_field_name)},
            exists.instance)

    if launch.tenant != exists.tenant:
        raise FieldMismatch(
            'tenant',
            {'name': 'exists', 'value': exists.tenant},
            {'name': 'launches', 'value': launch.tenant},
            exists.instance)

    if launch.rax_options != exists.rax_options:
        raise FieldMismatch(
            'rax_options',
            {'name': 'exists', 'value': exists.rax_options},
            {'name': 'launches', 'value': launch.rax_options},
            exists.instance)

    if launch.os_architecture != exists.os_architecture:
        raise FieldMismatch(
            'os_architecture',
            {'name': 'exists', 'value': exists.os_architecture},
            {'name': 'launches', 'value': launch.os_architecture},
            exists.instance)

    if launch.os_version != exists.os_version:
        raise FieldMismatch(
            'os_version',
            {'name': 'exists', 'value': exists.os_version},
            {'name': 'launches', 'value': launch.os_version},
            exists.instance)

    if launch.os_distro != exists.os_distro:
        raise FieldMismatch(
            'os_distro',
            {'name': 'exists', 'value': exists.os_distro},
            {'name': 'launches', 'value': launch.os_distro},
            exists.instance)


def _verify_for_launch(exist, launch=None,
                       launch_type="InstanceUsage"):

    if not launch and exist.usage:
        launch = exist.usage
    elif not launch:
        if models.InstanceUsage.objects\
                 .filter(instance=exist.instance).count() > 0:
            launches = models.InstanceUsage.find(
                exist.instance, dt.dt_from_decimal(exist.launched_at))
            count = launches.count()
            query = {
                'instance': exist.instance,
                'launched_at': exist.launched_at
            }
            if count > 1:
                raise AmbiguousResults(launch_type, query)
            elif count == 0:
                raise NotFound(launch_type, query)
            launch = launches[0]
        else:
            raise NotFound(launch_type, {'instance': exist.instance})

    _verify_field_mismatch(exist, launch)


def _verify_for_delete(exist, delete=None,
                       delete_type="InstanceDeletes"):

    if not delete and exist.delete:
        # We know we have a delete and we have it's id
        delete = exist.delete
    elif not delete:
        if exist.deleted_at:
            # We received this exists before the delete, go find it
            deletes = models.InstanceDeletes.find(
                exist.instance, dt.dt_from_decimal(exist.launched_at))
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
            launched_at = dt.dt_from_decimal(exist.launched_at)
            deleted_at_max = dt.dt_from_decimal(exist.audit_period_ending)
            deletes = models.InstanceDeletes.find(exist.instance, launched_at,
                                                  deleted_at_max)
            if deletes.count() > 0:
                reason = 'Found %s for non-delete exist' % delete_type
                raise VerificationException(reason)

    if delete:
        if not base_verifier._verify_date_field(
                delete.launched_at, exist.launched_at, same_second=True):
            raise FieldMismatch(
                'launched_at',
                {'name': 'exists', 'value': exist.launched_at},
                {'name': 'deletes', 'value': delete.launched_at},
                exist.instance)

        if not base_verifier._verify_date_field(
                delete.deleted_at, exist.deleted_at, same_second=True):
            raise FieldMismatch(
                'deleted_at',
                {'name': 'exists', 'value': exist.deleted_at},
                {'name': 'deletes', 'value': delete.deleted_at},
                exist.instance)


def _verify_basic_validity(exist):
    flavor_field_name = config.flavor_field_name()
    fields = {
        'tenant': exist.tenant,
        'launched_at': exist.launched_at,
        flavor_field_name: getattr(exist, flavor_field_name)
    }
    for (field_name, field_value) in fields.items():
        if field_value is None:
            raise NullFieldException(field_name, exist.id, exist.instance)
    base_verifier._is_hex_owner_id(
        'tenant', exist.tenant, exist.id, exist.instance)
    base_verifier._is_like_date(
        'launched_at', exist.launched_at, exist.id, exist.instance)
    if exist.deleted_at is not None:
        base_verifier._is_like_date(
            'deleted_at', exist.deleted_at, exist.id, exist.instance)


def _verify_optional_validity(exist):
    is_image_type_import = exist.is_image_type_import()
    fields = {exist.rax_options: 'rax_options',
              exist.os_architecture: 'os_architecture'
              }
    if not is_image_type_import:
        fields.update({exist.os_distro: 'os_distro',
                       exist.os_version: 'os_version'})
    for (field_value, field_name) in fields.items():
        if field_value == '':
            raise NullFieldException(field_name, exist.id, exist.instance)
    base_verifier._is_int_in_char(
        'rax_options', exist.rax_options, exist.id, exist.instance)
    base_verifier._is_alphanumeric(
        'os_architecture', exist.os_architecture, exist.id, exist.instance)
    if not is_image_type_import:
        base_verifier._is_alphanumeric(
            'os_distro', exist.os_distro, exist.id, exist.instance)
        base_verifier._is_alphanumeric(
            'os_version', exist.os_version, exist.id, exist.instance)


def _verify_validity(exist, validation_level):
    if validation_level == 'none':
        return
    if validation_level == 'basic':
        _verify_basic_validity(exist)
    if validation_level == 'all':
        _verify_basic_validity(exist)
        _verify_optional_validity(exist)


def _verify_with_reconciled_data(exist):
    if not exist.launched_at:
        raise VerificationException("Exists without a launched_at")

    query = models.InstanceReconcile.objects.filter(instance=exist.instance)
    if query.count() > 0:
        recs = models.InstanceReconcile.find(exist.instance,
                                             dt.dt_from_decimal((
                                             exist.launched_at)))
        search_query = {'instance': exist.instance,
                        'launched_at': exist.launched_at}
        count = recs.count()
        if count > 1:
            raise AmbiguousResults('InstanceReconcile', search_query)
        elif count == 0:
            raise NotFound('InstanceReconcile', search_query)
        reconcile = recs[0]
    else:
        raise NotFound('InstanceReconcile', {'instance': exist.instance})

    _verify_for_launch(exist, launch=reconcile,
                       launch_type="InstanceReconcile")
    delete = None
    if reconcile.deleted_at is not None:
        delete = reconcile
    _verify_for_delete(exist, delete=delete, delete_type="InstanceReconcile")


def _attempt_reconciled_verify(exist, orig_e):
    verified = False
    try:
        # Attempt to verify against reconciled data
        _verify_with_reconciled_data(exist)
        verified = True
        exist.mark_verified(reconciled=True)
    except NotFound, rec_e:
        # No reconciled data, just mark it failed
        exist.mark_failed(reason=str(orig_e))
    except VerificationException, rec_e:
        # Verification failed against reconciled data, mark it failed
        #    using the second failure.
        exist.mark_failed(reason=str(rec_e))
    except Exception, rec_e:
        exist.mark_failed(reason=rec_e.__class__.__name__)
        _get_child_logger().exception("nova: %s" % rec_e)
    return verified


def _verify(exist, validation_level):
    verified = False
    try:
        if not exist.launched_at:
            raise VerificationException("Exists without a launched_at")
        _verify_validity(exist, validation_level)
        _verify_for_launch(exist)
        _verify_for_delete(exist)

        verified = True
        exist.mark_verified()
    except VerificationException, orig_e:
        # Something is wrong with the InstanceUsage record
        verified = _attempt_reconciled_verify(exist, orig_e)
    except Exception, e:
        exist.mark_failed(reason=e.__class__.__name__)
        _get_child_logger().exception("nova: %s" % e)

    return verified, exist


class NovaVerifier(base_verifier.Verifier):

    def send_verified_notification(self, exist, connection, exchange,
                                   routing_keys=None):
        # NOTE (apmelton)
        # The exist we're provided from the callback may have cached queries
        # from before it was serialized. We don't want to use them as
        # they could have been lost somewhere in the process forking.
        # So, grab a new InstanceExists object from the database and use it.
        body = models.InstanceExists.objects.get(id=exist.id).raw.json
        json_body = json.loads(body)
        json_body[1]['event_type'] = self.config.nova_event_type()
        json_body[1]['original_message_id'] = json_body[1]['message_id']
        json_body[1]['message_id'] = str(uuid.uuid4())
        if routing_keys is None:
            message_service.send_notification(
                json_body[1], json_body[0], connection, exchange)
        else:
            for key in routing_keys:
                message_service.send_notification(
                    json_body[1], key, connection, exchange)

    def verify_exists(self, callback, exists, verifying_status):
        count = exists.count()
        added = 0
        update_interval = datetime.timedelta(seconds=30)
        next_update = datetime.datetime.utcnow() + update_interval
        _get_child_logger().info("nova: Adding %s exists to queue." % count)
        while added < count:
            for exist in exists[0:1000]:
                exist.update_status(verifying_status)
                exist.save()
                validation_level = self.config.validation_level()
                result = self.pool.apply_async(
                    _verify, args=(exist, validation_level),
                    callback=callback)
                self.results.append(result)
                added += 1
                if datetime.datetime.utcnow() > next_update:
                    values = ((added,) + self.clean_results())
                    msg = "nova: N: %s, P: %s, S: %s, E: %s" % values
                    _get_child_logger().info(msg)
                    next_update = datetime.datetime.utcnow() + update_interval
        return count

    def verify_for_range(self, ending_max, callback=None):
        sent_unverified_exists = models.InstanceExists.find(
            ending_max=ending_max, status=
            models.InstanceExists.SENT_UNVERIFIED)
        sent_unverified_count = self.verify_exists(None,
                                                   sent_unverified_exists,
                                                   models.InstanceExists.
                                                   SENT_VERIFYING)
        exists = models.InstanceExists.find(
            ending_max=ending_max, status=models.InstanceExists.PENDING)
        count = self.verify_exists(callback, exists,
                                   models.InstanceExists.VERIFYING)
        return count+sent_unverified_count

    def run_startup(self):
        logger = _get_child_logger()
        exists = models.InstanceExists.find(
            ending_max=self._utcnow(), status=models.InstanceExists.VERIFYING)
        count = exists.count()
        if count > 0:
            msg = "nova: Cleaning up %s exists stuck in VERIFYING status..." % count
            logger.info(msg)
            exists.update(status=models.InstanceExists.PENDING)

    def reconcile_failed(self):
        for failed_exist in self.failed:
            self.reconciler.failed_validation(failed_exist)
        self.failed = []

    def exchange(self):
        return 'nova'
