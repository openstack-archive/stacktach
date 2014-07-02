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
"""
    Usage: python usage_seed.py [period_length] [sql_connection]
    python usage_seed.py hour mysql://user:password@nova-db.example.com/nova?charset=utf8

    The idea behind usage seeding is to take the current state of all
    active instances on active compute hosts and insert that data into
    Stacktach's usage tables. This script should be run against the
    nova database in each cell which has active compute nodes. The
    reason for that is because the global cell does not have information
    on active compute hosts.
"""

import __builtin__
setattr(__builtin__, '_', lambda x: x)
import datetime
import os
import sys

from oslo.config import cfg
CONF = cfg.CONF

from nova.compute import task_states
from nova.context import RequestContext
from nova.db import api as novadb
from nova.db.sqlalchemy import api as sqlapi
from nova.db.sqlalchemy import models as novamodels

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from stacktach import datetime_to_decimal as dt
from stacktach import models

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Proper Usage: usage_seed.py [period_length] [sql_connection]"
        sys.exit(1)
    CONF.set_override("connection", sys.argv[2], group='database')


# start yanked from reports/nova_usage_audit.py
def get_previous_period(time, period_length):
    if period_length == 'day':
        last_period = time - datetime.timedelta(days=1)
        start = datetime.datetime(year=last_period.year,
                                  month=last_period.month,
                                  day=last_period.day)
        end = datetime.datetime(year=time.year,
                                month=time.month,
                                day=time.day)
        return start, end
    elif period_length == 'hour':
        last_period = time - datetime.timedelta(hours=1)
        start = datetime.datetime(year=last_period.year,
                                  month=last_period.month,
                                  day=last_period.day,
                                  hour=last_period.hour)
        end = datetime.datetime(year=time.year,
                                month=time.month,
                                day=time.day,
                                hour=time.hour)
        return start, end
# end yanked from reports/nova_usage_audit.py

inst_types = {}


def get_instance_type(type_id):
    global inst_types
    context = RequestContext('1', '1', is_admin=True)
    if type_id in inst_types:
        return inst_types[type_id]
    else:
        inst_type = sqlapi.model_query(context, novamodels.InstanceTypes)\
                          .filter_by(id=type_id).first()
        inst_types[type_id] = inst_type
        return inst_type


def get_metadata(instance_uuid):
    context = RequestContext('1', '1', is_admin=True)
    return sqlapi.instance_system_metadata_get(context, instance_uuid)


def _usage_for_instance(instance, task=None):
    usage = {
        'instance': instance['uuid'],
        'tenant': instance['project_id'],
        'instance_type_id': instance.get('instance_type_id'),
    }

    instance_type = get_instance_type(instance.get('instance_type_id'))
    usage['instance_flavor_id'] = instance_type['flavorid']

    metadata = get_metadata(instance['uuid'])
    usage['os_architecture'] = metadata.get('image_org.openstack__1__architecture')
    usage['os_distro'] = metadata.get('image_org.openstack__1__os_distro')
    usage['os_version'] = metadata.get('image_org.openstack__1__os_version')
    usage['rax_options'] = metadata.get('image_com.rackspace__1__options')

    launched_at = instance.get('launched_at')
    if launched_at is not None:
        usage['launched_at'] = dt.dt_to_decimal(launched_at)

    if task is not None:
        usage['task'] = task

    return usage


def _delete_for_instance(instance):
    delete = {
        'instance': instance['uuid'],
        'deleted_at': dt.dt_to_decimal(instance.get('deleted_at')),
    }

    launched_at = instance.get('launched_at')
    if launched_at is not None:
        delete['launched_at'] = dt.dt_to_decimal(launched_at)
    return delete


def get_computes():
    context = RequestContext('1', '1', is_admin=True)
    return sqlapi.model_query(context, novamodels.Service,
                              read_deleted='no')\
                 .filter_by(topic='compute').all()


def get_active_instances(period_length):
    start, end = get_previous_period(datetime.datetime.utcnow(), period_length)
    session = sqlapi.get_session()
    computes = get_computes()
    active_instances = []
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    for compute in computes:
        if compute.updated_at > yesterday:
            query = session.query(novamodels.Instance)
            active_filter = (novamodels.Instance.terminated_at == None,
                             novamodels.Instance.terminated_at > start)
            query = query.filter(sqlapi.or_(*active_filter))
            query = query.filter_by(host=compute.host)

            for instance in query.all():
                active_instances.append(instance)
    return active_instances


def get_action_for_instance(context, instance_uuid, action_name):
    actions = novadb.actions_get(context, instance_uuid)
    for action in actions:
        if action['action'] == action_name:
            return action


rebuild_tasks = [task_states.REBUILDING,
                 task_states.REBUILD_BLOCK_DEVICE_MAPPING,
                 task_states.REBUILD_SPAWNING]

resize_tasks = [task_states.RESIZE_PREP,
                task_states.RESIZE_MIGRATING,
                task_states.RESIZE_MIGRATED,
                task_states.RESIZE_FINISH]

resize_revert_tasks = [task_states.RESIZE_REVERTING]

rescue_tasks = [task_states.RESCUING]

in_flight_tasks = (rebuild_tasks + resize_tasks +
                   resize_revert_tasks + rescue_tasks)


def seed(period_length):
    usages = []
    building_usages = []
    in_flight_usages = []
    deletes = []


    start, end = get_previous_period(datetime.datetime.utcnow(), period_length)

    context = RequestContext(1, 1, is_admin=True)

    print "Selecting all active instances"
    active_instances = get_active_instances(period_length)
    print "Selected all active instances"

    print "Populating active usages, preparing for in-flight"
    for instance in active_instances:
        vm_state = instance['vm_state']
        task_state = instance['task_state']

        if vm_state == 'building':
            if instance['deleted'] != 0 and instance['deleted_at'] >= start:
                building_usages.append(_usage_for_instance(instance))
                deletes.append(_delete_for_instance(instance))
            elif instance['deleted'] == 0:
                building_usages.append(_usage_for_instance(instance))
        else:
            if task_state in in_flight_tasks:
                if (instance['deleted'] != 0 and
                        instance['deleted_at'] is not None and
                        instance['deleted_at'] >= start):
                    # Just in case...
                    deletes.append(_delete_for_instance(instance))
                    in_flight_usages.append(_usage_for_instance(instance,
                                            task=task_state))
                elif instance['deleted'] == 0:
                    in_flight_usages.append(_usage_for_instance(instance,
                                            task=task_state))
            else:
                if (instance['deleted'] != 0 and
                        instance['deleted_at'] is not None and
                        instance['deleted_at'] >= start):
                    deletes.append(_delete_for_instance(instance))
                    usages.append(_usage_for_instance(instance))
                elif instance['deleted'] == 0:
                    usages.append(_usage_for_instance(instance))

    print "Populated active instances, processing building"
    for usage in building_usages:
        action = get_action_for_instance(context, usage['instance'], 'create')
        if action is not None:
            usage['request_id'] = action['request_id']

    print "Populated building, processing in-flight"
    for usage in in_flight_usages:
        instance = usage['instance']
        action = None
        if usage['task'] in rebuild_tasks:
            action = get_action_for_instance(context, instance, 'rebuild')
        elif usage['task'] in resize_tasks:
            action = get_action_for_instance(context, instance, 'resize')
        elif usage['task'] in resize_revert_tasks:
            action = get_action_for_instance(context, instance, 'resizeRevert')
        elif usage['task'] in rescue_tasks:
            action = get_action_for_instance(context, instance, 'rescue')

        if action is not None:
            usage['request_id'] = action['request_id']
        del usage['task']

    print "Done cataloging usage"


    print "Saving active instances"
    active_InstanceUsages = map(lambda x: models.InstanceUsage(**x),
                                usages)
    models.InstanceUsage.objects.bulk_create(active_InstanceUsages,
                                             batch_size=100)

    print "Saving building instances"
    building_InstanceUsages = map(lambda x: models.InstanceUsage(**x),
                                  building_usages)
    models.InstanceUsage.objects.bulk_create(building_InstanceUsages,
                                             batch_size=100)

    print "Saving in-flight instances"
    in_flight_InstanceUsages = map(lambda x: models.InstanceUsage(**x),
                                   in_flight_usages)
    models.InstanceUsage.objects.bulk_create(in_flight_InstanceUsages,
                                             batch_size=100)

    print "Saving deletes"
    all_InstanceDeletes = map(lambda x: models.InstanceDeletes(**x),
                              deletes)
    models.InstanceDeletes.objects.bulk_create(all_InstanceDeletes,
                                               batch_size=100)

    return (len(usages), len(building_usages),
            len(in_flight_usages), len(deletes))

if __name__ == '__main__':
    msg = ("Seeded system with: \n"
           "%s Active Instances \n"
           "%s Building Instances \n"
           "%s In Flight Instances \n"
           "%s Deleted Instances \n")
    print msg % seed(sys.argv[1])

