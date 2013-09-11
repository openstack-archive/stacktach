# Copyright (c) 2013 - Rackspace Inc.
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
    db_api.configure_db()
    session = db_api.get_session()

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

