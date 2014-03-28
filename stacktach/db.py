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
from stacktach import stacklog
from stacktach import models


def _safe_get(Model, **kwargs):
    object = None
    query = Model.objects.filter(**kwargs)
    count = query.count()
    if count > 1:
        stacklog.warn('Multiple records found for %s get.' % Model.__name__)
        object = query[0]
    elif count < 1:
        stacklog.warn('No records found for %s get.' % Model.__name__)
    else:
        object = query[0]
    return object


def get_deployment(id):
    return _safe_get(models.Deployment, id=id)


def get_or_create_deployment(name):
    return models.Deployment.objects.get_or_create(name=name)


def create_nova_rawdata(**kwargs):
    imagemeta_fields = ['os_architecture', 'os_version',
                        'os_distro', 'rax_options']
    imagemeta_kwargs = \
        dict((k, v) for k, v in kwargs.iteritems() if k in imagemeta_fields)
    rawdata_kwargs = \
        dict((k, v) for k, v in kwargs.iteritems() if k not in imagemeta_fields)
    rawdata = models.RawData(**rawdata_kwargs)
    rawdata.save()

    imagemeta_kwargs.update({'raw_id': rawdata.id})
    save(models.RawDataImageMeta(**imagemeta_kwargs))

    return rawdata


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


def get_or_create_instance_usage(**kwargs):
    return models.InstanceUsage.objects.get_or_create(**kwargs)


def get_or_create_instance_delete(**kwargs):
    return models.InstanceDeletes.objects.get_or_create(**kwargs)


def get_instance_usage(**kwargs):
    return _safe_get(models.InstanceUsage, **kwargs)


def create_instance_delete(**kwargs):
    return models.InstanceDeletes(**kwargs)


def get_instance_delete(**kwargs):
    return _safe_get(models.InstanceDeletes, **kwargs)


def create_instance_exists(**kwargs):
    return models.InstanceExists(**kwargs)


def save(obj):
    obj.save()


def create_glance_rawdata(**kwargs):
    rawdata = models.GlanceRawData(**kwargs)
    rawdata.save()

    return rawdata


def create_generic_rawdata(**kwargs):
    rawdata = models.GenericRawData(**kwargs)
    rawdata.save()

    return rawdata


def create_image_usage(**kwargs):
    usage = models.ImageUsage(**kwargs)
    usage.save()

    return usage


def create_image_delete(**kwargs):
    delete = models.ImageDeletes(**kwargs)
    delete.save()

    return delete


def create_image_exists(**kwargs):
    exists = models.ImageExists(**kwargs)
    exists.save()

    return exists


def get_image_delete(**kwargs):
    return _safe_get(models.ImageDeletes, **kwargs)


def get_image_usage(**kwargs):
    return _safe_get(models.ImageUsage, **kwargs)
