import models

def create_rawdata(**kwargs):
    return models.RawData(**kwargs)

def create_lifecycle(**kwargs):
    return models.Lifecycle(**kwargs)

def find_lifecycles(**kwargs):
    return models.Lifecycle.objects.select_related().filter(**kwargs)

def create_timing(**kwargs):
    return models.Timing(**kwargs)

def find_timings(**kwargs):
    return models.Timing.objects.select_related().filter(**kwargs)

def create_request_tracker(**kwargs):
    return models.RequestTracker(**kwargs)

def find_request_trackers(**kwargs):
    return models.RequestTracker.objects.filter(**kwargs)

def create_instance_usage(**kwargs):
    return models.InstanceUsage(**kwargs)

def get_instance_usage(**kwargs):
    return models.InstanceUsage.objects.get(**kwargs)

def create_instance_exists(**kwargs):
    return models.InstanceExists(**kwargs)

def save(obj):
    obj.save()