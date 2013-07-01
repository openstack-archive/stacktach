from django import forms
from django.db import models


class Deployment(models.Model):
    name = models.CharField(max_length=50)

    def __repr__(self):
        return self.name


class GenericRawData(models.Model):
    deployment = models.ForeignKey(Deployment)
    tenant = models.CharField(max_length=50, null=True, blank=True,
                              db_index=True)
    json = models.TextField()
    routing_key = models.CharField(max_length=50, null=True,
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

    @staticmethod
    def get_name():
        return GenericRawData.__name__


class RawData(models.Model):
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

    @staticmethod
    def get_name():
        return RawData.__name__


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
    tenant = models.CharField(max_length=50, null=True, blank=True,
                              db_index=True)
    os_architecture = models.TextField(null=True, blank=True)
    os_distro = models.TextField(null=True, blank=True)
    os_version = models.TextField(null=True, blank=True)
    rax_options = models.TextField(null=True, blank=True)

    def deployment(self):
        raws = RawData.objects.filter(request_id=self.request_id)
        if raws.count() == 0:
            return False
        raw = raws[0]
        return raw.deployment


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
    tenant = models.CharField(max_length=50, null=True, blank=True,
                              db_index=True)
    os_architecture = models.TextField(null=True, blank=True)
    os_distro = models.TextField(null=True, blank=True)
    os_version = models.TextField(null=True, blank=True)
    rax_options = models.TextField(null=True, blank=True)
    source = models.CharField(max_length=150, null=True,
                              blank=True, db_index=True)


class InstanceExists(models.Model):
    PENDING = 'pending'
    VERIFYING = 'verifying'
    VERIFIED = 'verified'
    RECONCILED = 'reconciled'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (PENDING, 'Pending Verification'),
        (VERIFYING, 'Currently Being Verified'),
        (VERIFIED, 'Passed Verification'),
        (RECONCILED, 'Passed Verification After Reconciliation'),
        (FAILED, 'Failed Verification'),
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

    def deployment(self):
        return self.raw.deployment


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


class GlanceRawData(models.Model):
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


class ImageUsage(models.Model):
    uuid = models.CharField(max_length=50, db_index=True)
    created_at = models.DecimalField(max_digits=20,
                                     decimal_places=6, db_index=True)
    owner = models.CharField(max_length=50, db_index=True)
    size = models.BigIntegerField(max_length=20)
    last_raw = models.ForeignKey(GlanceRawData)


class ImageDeletes(models.Model):
    uuid = models.CharField(max_length=50, db_index=True)
    created_at = models.DecimalField(max_digits=20,
                                     decimal_places=6, db_index=True)
    deleted_at = models.DecimalField(max_digits=20,
                                     decimal_places=6, db_index=True)
    owner = models.CharField(max_length=50, db_index=True)
    size = models.BigIntegerField(max_length=20)
    raw = models.ForeignKey(GlanceRawData)


class ImageExists(models.Model):
    PENDING = 'pending'
    VERIFYING = 'verifying'
    VERIFIED = 'verified'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (PENDING, 'Pending Verification'),
        (VERIFYING, 'Currently Being Verified'),
        (VERIFIED, 'Passed Verification'),
        (FAILED, 'Failed Verification'),
    ]

    uuid = models.CharField(max_length=50, db_index=True)
    created_at = models.DecimalField(max_digits=20,
                                     decimal_places=6, db_index=True)
    deleted_at = models.DecimalField(max_digits=20,
                                     decimal_places=6, db_index=True)
    audit_period_beginning = models.DecimalField(max_digits=20,
                                                 decimal_places=6,
                                                 db_index=True)
    audit_period_ending = models.DecimalField(max_digits=20,
                                              decimal_places=6, db_index=True)
    status = models.CharField(max_length=50, db_index=True,
                              choices=STATUS_CHOICES,
                              default=PENDING)
    fail_reason = models.CharField(max_length=300, db_index=True, null=True)
    raw = models.ForeignKey(GlanceRawData, related_name='+')
    usage = models.ForeignKey(ImageUsage, related_name='+')
    delete = models.ForeignKey(ImageDeletes, related_name='+')
    send_status = models.IntegerField(default=0, db_index=True)
    owner = models.CharField(max_length=255, db_index=True)
    size = models.BigIntegerField(max_length=20)


def get_model_fields(model):
    return model._meta.fields
