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
import os
import sys

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from django.db.models import Min

from stacktach import models


if __name__ != '__main__':
    sys.exit(1)


def add_past_exists(start, end):
    exists = models.InstanceExists.objects.select_related()\
                                  .filter(audit_period_beginning=start,
                                          audit_period_ending=end)
    i = 0
    for exist in exists:
        i += 1
        print i
        if models.InstanceUsage.objects\
                 .filter(instance=exist.instance).count() == 0:
            # We got an exist record that we don't have any launches for
            values = {'instance': exist.instance,
                      'launched_at': exist.launched_at,
                      'instance_type_id': exist.instance_type_id,
                      'request_id': 'req-fake'}
            print values
            models.InstanceUsage(**values).save()


def find_earliest_daily_audit_period_beginning():
    where = 'audit_period_ending = audit_period_beginning + (60*60*24)'
    query = models.InstanceExists.objects.extra(where=[where])\
                                 .aggregate(Min('audit_period_beginning'))

    return query['audit_period_beginning__min']


start = find_earliest_daily_audit_period_beginning()
end = start + (60 * 60 * 24)

add_past_exists(start, end)
