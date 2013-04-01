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

import sys

sys.path.append("/stacktach")

from stacktach import datetime_to_decimal as dt
from stacktach import models


def _get_new_launches(beginning, ending):
    filters = {
        'launched_at__gte': beginning,
        'launched_at__lte': ending,
    }
    return models.InstanceUsage.objects.filter(**filters)


def _get_deletes(beginning, ending):
    filters = {
        'deleted_at__gte': beginning,
        'deleted_at__lte': ending,
    }
    return models.InstanceDeletes.objects.filter(**filters)


def _get_exists(beginning, ending):
    filters = {
        'audit_period_beginning': beginning,
        'audit_period_ending__gte': beginning,
        'audit_period_ending__lte': ending,
        'status': 'verified',
    }
    return models.InstanceExists.objects.filter(**filters)


def _audit_launches_to_exists(launches, exists):
    fails = []
    for (instance, launches) in launches.items():
        if instance in exists:
            for launch1 in launches:
                found = False
                for launch2 in exists[instance]:
                    if int(launch1['launched_at']) == int(launch2['launched_at']):
                    # HACK (apmelton): Truncate the decimal because we may not
                    #    have the milliseconds.
                        found = True

                if not found:
                    msg = "Couldn't find exists for launch (%s, %s)"
                    fails.append(msg % (instance, launch1['launched_at']))
        else:
            msg = "No exists for instance (%s)" % instance
            fails.append(msg)
    return fails


def _audit_exists_to_launches(exists, launches):
    fails = []
    for (instance, rows) in exists.items():
        if instance in launches:
            for exist in rows:
                found = False
                for launch in exists[instance]:
                    if int(exist['launched_at']) == int(launch['launched_at']):
                    # HACK (apmelton): Truncate the decimal because we may not
                    #    have the milliseconds.
                        found = True

                if not found:
                    msg = "Couldn't find exists for launch (%s, %s)"
                    fails.append(msg % (instance, exist['launched_at']))
        else:
            msg = "No launch for instance (%s)" % instance
            fails.append(msg)
    return fails


def _audit_for_period(beginning, ending):
    launches_dict = {}
    new_launches = _get_new_launches(beginning, ending)
    for launch in new_launches:
        instance = launch.instance
        l = {'id': launch.id, 'launched_at': launch.launched_at}
        if instance in launches_dict:
            launches_dict[instance].append(l)
        else:
            launches_dict[instance] = [l, ]

    deletes_dict = {}
    deletes = _get_deletes(beginning, ending)
    for delete in deletes:
        instance = delete.instance
        d = {'id': delete.id,
             'launched_at': delete.launched_at,
             'deleted_at': delete.deleted_at}
        if instance in deletes_dict:
            deletes_dict[instance].append(d)
        else:
            deletes_dict[instance] = [d, ]

    exists_dict = {}
    exists = _get_exists(beginning, ending)
    for exist in exists:
        instance = exist.instance
        e = {'id': exist.id,
             'launched_at': exist.launched_at,
             'deleted_at': exist.deleted_at}
        if instance in exists_dict:
            exists_dict[instance].append(e)
        else:
            exists_dict[instance] = [e, ]

    launch_to_exists_fails = _audit_launches_to_exists(launches_dict,
                                                       exists_dict)


def audit_for_period(beginning, ending):
    beginning_decimal = dt.dt_to_decimal(beginning)
    ending_decimal = dt.dt_to_decimal(ending)
    _audit_for_period(beginning_decimal, ending_decimal)