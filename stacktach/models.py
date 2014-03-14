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
import copy

from django.db import models
from django.db.models import Q

from stacktach import datetime_to_decimal as dt


def routing_key_type(key):
    if key.endswith('error'):
        return 'E'
    return ' '


class Deployment(models.Model):
    name = models.CharField(max_length=50)

    def __repr__(self):
        return self.name


class GenericRawData(models.Model):
    result_titles = [["#", "?", "When", "Deployment", "Event", "Host",
                      "Instance", "Request id"]]
    deployment = models.ForeignKey(Deployment)
    tenant = models.CharField(max_length=50, null=True, blank=True,
                              db_index=True)
    json = models.TextField()
    routing_key = models.CharField(max_length=50, null=True,
                                   blank=True, db_index=True)
    when = models.DecimalField(max_digits=20, decimal_places=6,
                                               db_index=True)
    publisher = models.CharField(max_length=100, null=True,
                                 blank=True, db_index=True)
    event = models.CharField(max_length=50, null=True,
                                 blank=True, db_index=True)
    service = models.CharField(max_length=50, null=True,
                                 blank=True, db_index=True)
    host = models.CharField(max_length=100, null=True,
                                 blank=True, db_index=True)
    instance = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)
    request_id = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)
    message_id = models.CharField(max_length=50, null=True,
                                  blank=True, db_index=True)

    @staticmethod
    def get_name():
        return GenericRawData.__name__

    @property
    def uuid(self):
        return self.instance

    def search_results(self, results, when, routing_key_status):
        if not results:
            results = copy.deepcopy(self.result_titles)
        results.append([self.id, routing_key_status, str(when),
                        self.deployment.name, self.event, self.host,
                        self.instance, self.request_id])
        return results


class RawData(models.Model):
    result_titles = [["#", "?", "When", "Deployment", "Event", "Host",
                          "State", "State'", "Task'"]]
    deployment = models.ForeignKey(Deployment)
    tenant = models.CharField(max_length=50, null=True, blank=True,
                              db_index=True)
    json = models.TextField()
    routing_key = models.CharField(max_length=50, null=True,
                                   blank=True, db_index=True)
    state = models.CharField(max_length=20, null=True,
                             blank=True, db_index=True)
    old_state = models.CharField(max_length=20, null=True,
                             blank=True, db_index=True)
    old_task = models.CharField(max_length=30, null=True,
                             blank=True, db_index=True)
    task = models.CharField(max_length=30, null=True,
                             blank=True, db_index=True)
    image_type = models.IntegerField(null=True, default=0, db_index=True)
    when = models.DecimalField(max_digits=20, decimal_places=6,
                                               db_index=True)
    publisher = models.CharField(max_length=100, null=True,
                                 blank=True, db_index=True)
    event = models.CharField(max_length=50, null=True,
                                 blank=True, db_index=True)
    service = models.CharField(max_length=50, null=True,
                                 blank=True, db_index=True)
    host = models.CharField(max_length=100, null=True,
                                 blank=True, db_index=True)
    instance = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)
    request_id = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)

    def __repr__(self):
        return "%s %s %s" % (self.event, self.instance, self.state)

    @property
    def uuid(self):
        return self.instance

    @staticmethod
    def get_name():
        return RawData.__name__

    def search_results(self, results, when, routing_key_status):
        if not results:
            results = copy.deepcopy(self.result_titles)
        results.append([self.id, routing_key_status, str(when),
                        self.deployment.name, self.event, self.host, self.state,
                        self.old_state, self.old_task])
        return results


class RawDataImageMeta(models.Model):
    raw = models.ForeignKey(RawData, null=False)
    os_architecture = models.TextField(null=True, blank=True)
    os_distro = models.TextField(null=True, blank=True)
    os_version = models.TextField(null=True, blank=True)
    rax_options = models.TextField(null=True, blank=True)


class Lifecycle(models.Model):
    """The Lifecycle table is the Master for a group of
    Timing detail records. There is one Lifecycle row for
    each instance seen in the event stream. The Timings
    relate to the execution time for each .start/.end event
    pair for this instance. These pairs are over the entire
    lifespan of the instance, even across multiple api requests."""
    instance = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)
    last_state = models.CharField(max_length=50, null=True,
                             blank=True, db_index=True)
    last_task_state = models.CharField(max_length=50, null=True,
                             blank=True, db_index=True)
    last_raw = models.ForeignKey(RawData, null=True)


class InstanceUsage(models.Model):
    instance = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)
    launched_at = models.DecimalField(null=True, max_digits=20,
                                      decimal_places=6, db_index=True)
    request_id =  models.CharField(max_length=50, null=True,
                                   blank=True, db_index=True)
    instance_type_id =  models.CharField(max_length=50,
                                         null=True,
                                         blank=True,
                                         db_index=True)
    instance_flavor_id = models.CharField(max_length=100, null=True,
                                          blank=True, db_index=True)
    tenant = models.CharField(max_length=50, null=True, blank=True,
                              db_index=True)
    os_architecture = models.TextField(null=True, blank=True)
    os_distro = models.TextField(null=True, blank=True)
    os_version = models.TextField(null=True, blank=True)
    rax_options = models.TextField(null=True, blank=True)

    def deployment(self):
        raws = RawData.objects.filter(request_id=self.request_id)
        return raws and raws[0].deployment

    def latest_deployment_for_request_id(self):
        raw = self.latest_raw_for_request_id()
        return raw and raw.deployment

    def latest_raw_for_request_id(self):
        return self.request_id and RawData.objects.filter(
            request_id=self.request_id).order_by('-id')[0]

    def host(self):
        raw = self.latest_raw_for_request_id()
        return raw and raw.host

    @staticmethod
    def find(instance, launched_at):
        start = launched_at - datetime.timedelta(
            microseconds=launched_at.microsecond)
        end = start + datetime.timedelta(microseconds=999999)
        params = {'instance': instance,
                  'launched_at__gte': dt.dt_to_decimal(start),
                  'launched_at__lte': dt.dt_to_decimal(end)}
        return InstanceUsage.objects.filter(**params)


class InstanceDeletes(models.Model):
    instance = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)
    launched_at = models.DecimalField(null=True, max_digits=20,
                                      decimal_places=6, db_index=True)
    deleted_at = models.DecimalField(null=True, max_digits=20,
                                     decimal_places=6, db_index=True)
    raw = models.ForeignKey(RawData, null=True)

    def deployment(self):
        return self.raw.deployment

    @staticmethod
    def find(instance, launched, deleted_max=None):
        start = launched - datetime.timedelta(microseconds=launched.microsecond)
        end = start + datetime.timedelta(microseconds=999999)
        params = {'instance': instance,
                  'launched_at__gte': dt.dt_to_decimal(start),
                  'launched_at__lte': dt.dt_to_decimal(end)}
        if deleted_max:
            params['deleted_at__lte'] = dt.dt_to_decimal(deleted_max)
        return InstanceDeletes.objects.filter(**params)


class InstanceReconcile(models.Model):
    row_created = models.DateTimeField(auto_now_add=True)
    row_updated = models.DateTimeField(auto_now=True)
    instance = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)
    launched_at = models.DecimalField(null=True, max_digits=20,
                                      decimal_places=6, db_index=True)
    deleted_at = models.DecimalField(null=True, max_digits=20,
                                     decimal_places=6, db_index=True)
    instance_type_id = models.CharField(max_length=50,
                                        null=True,
                                        blank=True,
                                        db_index=True)
    instance_flavor_id = models.CharField(max_length=100, null=True,
                                          blank=True, db_index=True)
    tenant = models.CharField(max_length=50, null=True, blank=True,
                              db_index=True)
    os_architecture = models.TextField(null=True, blank=True)
    os_distro = models.TextField(null=True, blank=True)
    os_version = models.TextField(null=True, blank=True)
    rax_options = models.TextField(null=True, blank=True)
    source = models.CharField(max_length=150, null=True,
                              blank=True, db_index=True)

    @staticmethod
    def find(instance, launched):
        start = launched - datetime.timedelta(microseconds=launched.microsecond)
        end = start + datetime.timedelta(microseconds=999999)
        params = {'instance': instance,
                  'launched_at__gte': dt.dt_to_decimal(start),
                  'launched_at__lte': dt.dt_to_decimal(end)}
        return InstanceReconcile.objects.filter(**params)


class InstanceExists(models.Model):
    PENDING = 'pending'
    VERIFYING = 'verifying'
    VERIFIED = 'verified'
    RECONCILED = 'reconciled'
    FAILED = 'failed'
    SENT_UNVERIFIED = 'sent_unverified'
    SENT_FAILED = 'sent_failed'
    SENT_VERIFYING = 'sent_verifying'
    STATUS_CHOICES = [
        (PENDING, 'Pending Verification'),
        (VERIFYING, 'Currently Being Verified'),
        (VERIFIED, 'Passed Verification'),
        (RECONCILED, 'Passed Verification After Reconciliation'),
        (FAILED, 'Failed Verification'),
        (SENT_UNVERIFIED, 'Unverified but sent by Yagi'),
        (SENT_FAILED, 'Failed Verification but sent by Yagi'),
        (SENT_VERIFYING, 'Currently being verified but sent by Yagi')
    ]

    instance = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)
    launched_at = models.DecimalField(null=True, max_digits=20,
                                      decimal_places=6, db_index=True)
    deleted_at = models.DecimalField(null=True, max_digits=20,
                                     decimal_places=6, db_index=True)
    audit_period_beginning = models.DecimalField(null=True, max_digits=20,
                                                 decimal_places=6,
                                                 db_index=True)
    audit_period_ending = models.DecimalField(null=True, max_digits=20,
                                              decimal_places=6, db_index=True)
    message_id = models.CharField(max_length=50, null=True,
                                  blank=True, db_index=True)
    instance_type_id = models.CharField(max_length=50,
                                        null=True,
                                        blank=True,
                                        db_index=True)
    status = models.CharField(max_length=50, db_index=True,
                              choices=STATUS_CHOICES,
                              default=PENDING)
    fail_reason = models.CharField(max_length=300, null=True,
                                   blank=True, db_index=True)
    raw = models.ForeignKey(RawData, related_name='+', null=True)
    usage = models.ForeignKey(InstanceUsage, related_name='+', null=True)
    delete = models.ForeignKey(InstanceDeletes, related_name='+', null=True)
    send_status = models.IntegerField(null=True, default=0, db_index=True)
    tenant = models.CharField(max_length=50, null=True, blank=True,
                              db_index=True)
    os_architecture = models.TextField(null=True, blank=True)
    os_distro = models.TextField(null=True, blank=True)
    os_version = models.TextField(null=True, blank=True)
    rax_options = models.TextField(null=True, blank=True)
    bandwidth_public_out = models.BigIntegerField(default=0)
    instance_flavor_id = models.CharField(max_length=100, null=True,
                                          blank=True, db_index=True)
    event_id = models.CharField(max_length=50, null=True,blank=True)

    def deployment(self):
        return self.raw.deployment

    @staticmethod
    def find(ending_max, status):
        params = {'audit_period_ending__lte': dt.dt_to_decimal(ending_max),
                  'status': status}
        return InstanceExists.objects.select_related()\
            .filter(**params).order_by('id')

    def mark_verified(self, reconciled=False, reason=None):
        if not reconciled:
            self.status = InstanceExists.VERIFIED
        else:
            self.status = InstanceExists.RECONCILED
            if reason is not None:
                self.fail_reason = reason

        self.save()

    def mark_failed(self, reason=None):
        if self.status == InstanceExists.SENT_VERIFYING:
            self.status = InstanceExists.SENT_FAILED
        else:
            self.status = InstanceExists.FAILED
        if reason:
            self.fail_reason = reason
        self.save()

    def update_status(self, new_status):
        self.status = new_status

    def is_image_type_import(self):
        return (self.raw.image_type & 0xf) == 3

    @staticmethod
    def mark_exists_as_sent_unverified(message_ids):
        absent_exists = []
        exists_not_pending = []
        for message_id in message_ids:
            try:
                exists = InstanceExists.objects.get(message_id=message_id)
                if exists.status == InstanceExists.PENDING:
                    exists.status = InstanceExists.SENT_UNVERIFIED
                    exists.send_status = '201'
                    exists.save()
                else:
                    exists_not_pending.append(message_id)
            except Exception:
                absent_exists.append(message_id)
        return absent_exists, exists_not_pending




class Timing(models.Model):
    """Each Timing record corresponds to a .start/.end event pair
    for an instance. It tracks how long it took this operation
    to execute."""
    name = models.CharField(max_length=50, db_index=True)
    lifecycle = models.ForeignKey(Lifecycle)
    start_raw = models.ForeignKey(RawData, related_name='+', null=True)
    end_raw = models.ForeignKey(RawData, related_name='+', null=True)

    start_when = models.DecimalField(null=True, max_digits=20,
                                     decimal_places=6)
    end_when = models.DecimalField(null=True, max_digits=20, decimal_places=6)

    diff = models.DecimalField(null=True, max_digits=20, decimal_places=6,
                               db_index=True)


class RequestTracker(models.Model):
    """The RequestTracker table tracks the elapsed time of a user
    request from the time it hits the API node to the time of the
    final .end event (with the same Request ID)."""
    request_id = models.CharField(max_length=50, db_index=True)
    lifecycle = models.ForeignKey(Lifecycle)
    last_timing = models.ForeignKey(Timing, null=True, db_index=True)
    start = models.DecimalField(max_digits=20, decimal_places=6, db_index=True)
    duration = models.DecimalField(max_digits=20, decimal_places=6,
                                   db_index=True)

    # Not used ... but soon hopefully.
    completed = models.BooleanField(default=False, db_index=True)


class JsonReport(models.Model):
    """Stores cron-job reports in raw json format for extraction
       via stacky/rest. All DateTimes are UTC."""
    period_start = models.DateTimeField(db_index=True)
    period_end = models.DateTimeField(db_index=True)
    created = models.DecimalField(max_digits=20, decimal_places=6, db_index=True)
    name = models.CharField(max_length=50, db_index=True)
    version = models.IntegerField(default=1)
    json = models.TextField()


class TenantType(models.Model):
    name = models.CharField(max_length=50, db_index=True)
    value = models.CharField(max_length=50, db_index=True)


class TenantInfo(models.Model):
    """This contains tenant information synced from an external source.
    It's mostly used as a cache to put things like tenant name on reports
    without making alot of calls to an external system."""
    tenant = models.CharField(max_length=50, db_index=True, unique=True)
    name = models.CharField(max_length=100, null=True,
                            blank=True, db_index=True)
    types = models.ManyToManyField(TenantType)
    last_updated = models.DateTimeField(db_index=True)


class GlanceRawData(models.Model):
    result_titles = [["#", "?", "When", "Deployment", "Event", "Host",
                          "Status"]]
    ACTIVE = 'active'
    DELETED = 'deleted'
    KILLED = 'killed'
    PENDING_DELETE = 'pending_delete'
    QUEUED = 'queued'
    SAVING = 'saving'
    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (DELETED, 'Deleted'),
        (KILLED, 'Killed'),
        (PENDING_DELETE, 'Pending delete'),
        (QUEUED, 'Queued'),
        (SAVING, 'Saving'),
    ]

    deployment = models.ForeignKey(Deployment)
    owner = models.CharField(max_length=255, null=True, blank=True,
                             db_index=True)
    json = models.TextField()
    routing_key = models.CharField(max_length=50, null=True, blank=True,
                                   db_index=True)
    when = models.DecimalField(max_digits=20, decimal_places=6, db_index=True)
    publisher = models.CharField(max_length=100, null=True,
                                 blank=True, db_index=True)
    event = models.CharField(max_length=50, null=True, blank=True,
                             db_index=True)
    service = models.CharField(max_length=50, null=True, blank=True,
                               db_index=True)
    host = models.CharField(max_length=100, null=True, blank=True,
                            db_index=True)
    instance = models.CharField(max_length=50, null=True, blank=True,
                                db_index=True)
    request_id = models.CharField(max_length=50, null=True, blank=True,
                                  db_index=True)
    uuid = models.CharField(max_length=36, null=True, blank=True,
                            db_index=True)
    status = models.CharField(max_length=30, db_index=True,
                              choices=STATUS_CHOICES, null=True)
    image_type = models.IntegerField(null=True, default=0, db_index=True)

    @staticmethod
    def get_name():
        return GlanceRawData.__name__

    def search_results(self, results, when, routing_key_status):
        if not results:
            results = copy.deepcopy(self.result_titles)
        results.append([self.id, routing_key_status, str(when),
                            self.deployment.name, self.event, self.host,
                            self.status])
        return results


class ImageUsage(models.Model):
    uuid = models.CharField(max_length=50, db_index=True)
    created_at = models.DecimalField(max_digits=20,
                                     decimal_places=6, db_index=True)
    owner = models.CharField(max_length=50, db_index=True, null=True)
    size = models.BigIntegerField(max_length=20)
    last_raw = models.ForeignKey(GlanceRawData, null=True)


class ImageDeletes(models.Model):
    uuid = models.CharField(max_length=50, db_index=True)
    deleted_at = models.DecimalField(max_digits=20,
                                     decimal_places=6, db_index=True,
                                     null=True)
    raw = models.ForeignKey(GlanceRawData, null=True)

    @staticmethod
    def find(uuid, deleted_max=None):
        params = {'uuid': uuid}
        if deleted_max:
            params['deleted_at__lte'] = dt.dt_to_decimal(deleted_max)
        return ImageDeletes.objects.filter(**params)


class ImageExists(models.Model):
    PENDING = 'pending'
    VERIFYING = 'verifying'
    VERIFIED = 'verified'
    FAILED = 'failed'
    SENT_UNVERIFIED = 'sent_unverified'
    SENT_FAILED = 'sent_failed'
    SENT_VERIFYING = 'sent_verifying'
    STATUS_CHOICES = [
        (PENDING, 'Pending Verification'),
        (VERIFYING, 'Currently Being Verified'),
        (VERIFIED, 'Passed Verification'),
        (FAILED, 'Failed Verification'),
        (SENT_UNVERIFIED, 'Unverified but sent by Yagi'),
        (SENT_FAILED, 'Failed Verification but sent by Yagi'),
        (SENT_VERIFYING, 'Currently being verified but sent by Yagi')
    ]

    uuid = models.CharField(max_length=50, db_index=True, null=True)
    created_at = models.DecimalField(max_digits=20,
                                     decimal_places=6, db_index=True,
                                     null=True)
    deleted_at = models.DecimalField(max_digits=20,
                                     decimal_places=6, db_index=True,
                                     null=True)
    audit_period_beginning = models.DecimalField(max_digits=20,
                                                 decimal_places=6,
                                                 db_index=True)
    audit_period_ending = models.DecimalField(max_digits=20,
                                              decimal_places=6, db_index=True)
    status = models.CharField(max_length=50, db_index=True,
                              choices=STATUS_CHOICES,
                              default=PENDING)
    fail_reason = models.CharField(max_length=300, null=True)
    raw = models.ForeignKey(GlanceRawData, related_name='+')
    usage = models.ForeignKey(ImageUsage, related_name='+', null=True)
    delete = models.ForeignKey(ImageDeletes, related_name='+', null=True)
    send_status = models.IntegerField(default=0, db_index=True)
    owner = models.CharField(max_length=255, db_index=True, null=True)
    size = models.BigIntegerField(max_length=20)
    message_id = models.CharField(max_length=50, null=True,
                                  blank=True, db_index=True)
    event_id = models.CharField(max_length=50, null=True,blank=True)


    def update_status(self, new_status):
        self.status = new_status

    @staticmethod
    def find_and_group_by_owner_and_raw_id(ending_max, status):
        params = {'audit_period_ending__lte': dt.dt_to_decimal(ending_max),
                  'status': status}
        ordered_exists = ImageExists.objects.select_related().\
            filter(**params).order_by('owner')
        result = {}
        for exist in ordered_exists:
            key = "%s-%s" % (exist.owner, exist.raw_id)
            if key in result:
                result[key].append(exist)
            else:
                result[key] = [exist]
        return result

    def mark_verified(self):
        self.status = InstanceExists.VERIFIED
        self.save()

    def mark_failed(self, reason=None):
        if self.status == ImageExists.SENT_VERIFYING:
            self.status = ImageExists.SENT_FAILED
        else:
            self.status = ImageExists.FAILED
        if reason:
            self.fail_reason = reason
        self.save()

    @staticmethod
    def mark_exists_as_sent_unverified(message_ids):
        absent_exists = []
        exists_not_pending = []
        for message_id in message_ids:
            exists_list = ImageExists.objects.filter(message_id=message_id)
            if exists_list:
                for exists in exists_list:
                    if exists.status == ImageExists.PENDING:
                        exists.status = ImageExists.SENT_UNVERIFIED
                        exists.send_status = '201'
                        exists.save()
                    else:
                        exists_not_pending.append(message_id)
            else :
                absent_exists.append(message_id)
        return absent_exists, exists_not_pending



def get_model_fields(model):
    return model._meta.fields
