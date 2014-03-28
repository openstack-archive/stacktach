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
    Usage: python glance_usage_seed.py [period_length] [sql_connection]
    python glance_usage_seed.py hour mysql://user:password@nova-db.example
    .com/nova?charset=utf8

    The idea behind glance_usage seeding is to take the current state of all
    active, deleted and pending_delete images from glance and insert that
    data into Stacktach's image_usage and image_deletes tables.
"""

import __builtin__
setattr(__builtin__, '_', lambda x: x)
import datetime
import os
import sys
from oslo.config import cfg

CONF = cfg.CONF
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Proper Usage: glance_usage_seed.py [period_length] [" \
              "sql_connection]"
        sys.exit(1)
    CONF.sql_connection = sys.argv[2]

import glance.context
import glance.db.sqlalchemy.api as db_api
from sqlalchemy import or_
from sqlalchemy import and_
import glance.db.sqlalchemy.api as db_api
from glance.db.sqlalchemy import models as glancemodels

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'stacktach')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from stacktach import datetime_to_decimal as dt
from stacktach import models


# start yanked from reports/nova_usage_audit.py
def get_period_start(time, period_length):
    if period_length == 'day':
        last_period = time - datetime.timedelta(days=1)
        start = datetime.datetime(year=last_period.year,
                                  month=last_period.month,
                                  day=last_period.day)
        return start
    elif period_length == 'hour':
        last_period = time - datetime.timedelta(hours=1)
        start = datetime.datetime(year=last_period.year,
                                  month=last_period.month,
                                  day=last_period.day,
                                  hour=last_period.hour)
        return start
# end yanked from reports/nova_usage_audit.py


def _usage_for_image(image):
    return {
        'uuid': image.id,
        'owner': image.owner,
        'created_at': dt.dt_to_decimal(image.created_at),
        'owner': image.owner,
        'size': image.size,
        'last_raw_id': None
    }


def _delete_for_image(image):
    return {
        'uuid': image.id,
        'deleted_at': dt.dt_to_decimal(image.deleted_at),
        'raw_id': None
    }


def _get_usages(start, session):
    usage_filter = (glancemodels.Image.status == 'active',
                    glancemodels.Image.deleted_at > start)
    query = session.query(glancemodels.Image)
    images = query.filter(or_(*usage_filter)).all()
    return [_usage_for_image(image) for image in images]


def _get_deletes(start, session):
    delete_filter = (glancemodels.Image.status == 'deleted',
                     glancemodels.Image.deleted_at > start)
    query = session.query(glancemodels.Image)
    images = query.filter(and_(*delete_filter)).all()
    return [_delete_for_image(image) for image in images]


def seed(period_length):
    start = get_period_start(datetime.datetime.utcnow(), period_length)
    db_api.setup_db_env()
    session = db_api._get_session()

    print "Populating active image usages"
    usages = _get_usages(start, session)

    if usages:
        print "Saving active image images"
        active_images = map(lambda x: models.ImageUsage(**x), usages)
        models.ImageUsage.objects.bulk_create(active_images, batch_size=100)

    print "Populating image deletes"
    deletes = _get_deletes(start, session)

    if deletes:
        print "Saving image deletes"
        deleted_images = map(lambda x: models.ImageDeletes(**x), deletes)
        models.ImageDeletes.objects.bulk_create(deleted_images, batch_size=100)

    print "Seeding completed"
    return len(usages), len(deletes)

if __name__ == '__main__':
    msg = ("Seeded system with: \n"
           "%s Active images \n"
           "%s Deleted images \n")
    period = sys.argv[1]
    print msg % seed(period)

