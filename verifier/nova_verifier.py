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
import json
import os
import sys
import uuid


POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from verifier import base_verifier
from verifier import NullFieldException
from stacktach import models
from stacktach import datetime_to_decimal as dt
from verifier import FieldMismatch
from verifier import AmbiguousResults
from verifier import NotFound
from verifier import VerificationException
from stacktach import stacklog, message_service
LOG = stacklog.get_logger('verifier')


def _verify_field_mismatch(exists, launch):
    if not base_verifier._verify_date_field(
            launch.launched_at, exists.launched_at, same_second=True):
        raise FieldMismatch('launched_at', exists.launched_at,
                            launch.launched_at)

    if launch.instance_type_id != exists.instance_type_id:
        raise FieldMismatch('instance_type_id', exists.instance_type_id,
                            launch.instance_type_id)

    if launch.tenant != exists.tenant:
        raise FieldMismatch('tenant', exists.tenant,
                            launch.tenant)

    if launch.rax_options != exists.rax_options:
        raise FieldMismatch('rax_options', exists.rax_options,
                            launch.rax_options)

    if launch.os_architecture != exists.os_architecture:
        raise FieldMismatch('os_architecture', exists.os_architecture,
                            launch.os_architecture)

    if launch.os_version != exists.os_version:
        raise FieldMismatch('os_version', exists.os_version,
                            launch.os_version)

    if launch.os_distro != exists.os_distro:
        raise FieldMismatch('os_distro', exists.os_distro,
                            launch.os_distro)


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
            raise FieldMismatch('launched_at', exist.launched_at,
                                delete.launched_at)

        if not base_verifier._verify_date_field(
                delete.deleted_at, exist.deleted_at, same_second=True):
            raise FieldMismatch(
                'deleted_at', exist.deleted_at, delete.deleted_at)


def _verify_basic_validity(exist):
    fields = {exist.tenant: 'tenant',
              exist.launched_at: 'launched_at',
              exist.instance_type_id: 'instance_type_id'}
    for (field_value, field_name) in fields.items():
        if field_value is None:
            raise NullFieldException(field_name, exist.id)
    base_verifier._is_hex_owner_id('tenant', exist.tenant, exist.id)
    base_verifier._is_like_date('launched_at', exist.launched_at, exist.id)
    if exist.deleted_at is not None:
        base_verifier._is_like_date('deleted_at', exist.deleted_at, exist.id)


def _verify_optional_validity(exist):
    fields = {exist.rax_options: 'rax_options',
              exist.os_architecture: 'os_architecture',
              exist.os_version: 'os_version',
              exist.os_distro: 'os_distro'}
    for (field_value, field_name) in fields.items():
        if field_value == '':
            raise NullFieldException(field_name, exist.id)
    base_verifier._is_int_in_char('rax_options', exist.rax_options, exist.id)
    base_verifier._is_alphanumeric('os_architecture', exist.os_architecture, exist.id)
    base_verifier._is_alphanumeric('os_distro', exist.os_distro, exist.id)
    base_verifier._is_alphanumeric('os_version', exist.os_version, exist.id)

def verify_fields_not_null(exist_id, null_value, fields):

    for (field_value, field_name) in fields.items():
        print "value: %s, name = %s" % (field_value, field_name)
        if field_value == null_value:
            raise NullFieldException(field_name, exist_id)


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
        LOG.exception("nova: %s" % rec_e)
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
        LOG.exception("nova: %s" % e)

    return verified, exist


class NovaVerifier(base_verifier.Verifier):
    def __init__(self, config, pool=None, reconciler=None):
        super(NovaVerifier, self).__init__(config,
                                           pool=pool,
                                           reconciler=reconciler)

    def send_verified_notification(self, exist, connection, exchange,
                                   routing_keys=None):
        body = exist.raw.json
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

    def verify_for_range(self, ending_max, callback=None):
        exists = models.InstanceExists.find(
            ending_max=ending_max, status=models.InstanceExists.PENDING)
        count = exists.count()
        added = 0
        update_interval = datetime.timedelta(seconds=30)
        next_update = datetime.datetime.utcnow() + update_interval
        LOG.info("nova: Adding %s exists to queue." % count)
        while added < count:
            for exist in exists[0:1000]:
                exist.update_status(models.InstanceExists.VERIFYING)
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
                    LOG.info(msg)
                    next_update = datetime.datetime.utcnow() + update_interval
        return count

    def reconcile_failed(self):
        for failed_exist in self.failed:
            self.reconciler.failed_validation(failed_exist)
        self.failed = []

    def exchange(self):
        return 'nova'
