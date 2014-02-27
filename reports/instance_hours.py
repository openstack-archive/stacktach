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
import argparse
import datetime
import json
import math
import sys
import operator
import os

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))

import usage_audit

from stacktach import datetime_to_decimal as dt
from stacktach import models
from stacktach import stacklog


class TenantManager(object):
    def __init__(self):
        self._types = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    @property
    def type_names(self):
        if self._types is None:
            self._types = set()
            for t in models.TenantType.objects.all():
                self._types.add(t.name)
        return self._types

    def get_tenant_info(self, tenant_id):
        try:
            tenant = models.TenantInfo.objects\
                                      .get(tenant=tenant_id)
            tenant_info = dict(
                     tenant=tenant_id, 
                     account_name=tenant.name)
            ttypes = dict()
            for t in tenant.types.all():
                ttypes[t.name] = t.value
        except models.TenantInfo.DoesNotExist:
            tenant_info = dict(
                     tenant=tenant_id, 
                     account_name='unknown account')
            ttypes = dict()
            for t in self.type_names:
                ttypes[t] = 'unknown'
        tenant_info['types'] = ttypes
        return tenant_info


class InstanceHoursReport(object):

    FLAVOR_CLASS_WEIGHTS = dict(standard=1.0)

    def __init__(self, tenant_manager, time=None, period_length='day'):
        if time is None:
            time = datetime.datetime.utcnow()
        self.start, self.end = usage_audit.get_previous_period(time, period_length)
        self.tenant_manager = tenant_manager
        self.flavor_cache = dict()
        self.clear()

    def clear(self):
        self.count = 0 
        self.unit_hours = 0.0
        self.by_flavor = dict()
        self.by_flavor_class = dict()
        self.by_tenant = dict()
        self.by_type = dict()
        for name in self.tenant_manager.type_names:
            self.by_tenant[name] = dict()
            self.by_type[name] = dict()

    def _get_verified_exists(self):
        start = dt.dt_to_decimal(self.start)
        end = dt.dt_to_decimal(self.end)
        return models.InstanceExists.objects.filter(
            status=models.InstanceExists.VERIFIED,
            audit_period_beginning__gte=start,
            audit_period_beginning__lte=end,
            audit_period_ending__gte=start,
            audit_period_ending__lte=end)

    def _get_instance_hours(self, exist):
        if (exist.deleted_at is None) or (exist.deleted_at > exist.audit_period_ending):
            end = exist.audit_period_ending
        else:
            end = exist.deleted_at
        if exist.launched_at > exist.audit_period_beginning:
            start = exist.launched_at
        else:
            start = exist.audit_period_beginning
        return math.ceil((end - start)/3600)

    def _get_flavor_info(self, exist):
        flavor = exist.instance_flavor_id
        if flavor not in self.flavor_cache:
            if '-' in flavor:
                flavor_class, n = flavor.split('-', 1)
            else:
                flavor_class = 'standard'
            try:
                payload = json.loads(exist.raw.json)[1]['payload']
            except Exception:
                print "Error loading raw notification data for %s" % exist.id
                raise
            flavor_name = payload['instance_type']
            flavor_size = payload['memory_mb']
            weight = self.FLAVOR_CLASS_WEIGHTS.get(flavor_class, 1.0)
            flavor_units = (flavor_size/256.0) * weight
            self.flavor_cache[flavor] = (flavor, flavor_name, flavor_class, flavor_units)
        return self.flavor_cache[flavor]

    def add_type_hours(self, type_name, type_value, unit_hours):
        if type_value not in self.by_type[type_name]:
            self.by_type[type_name][type_value] = dict(count=0, unit_hours=0.0)
        cts = self.by_type[type_name][type_value]
        cts['count'] += 1
        cts['unit_hours'] += unit_hours
        cts['percent_count'] = (float(cts['count'])/self.count) * 100
        cts['percent_unit_hours'] = (cts['unit_hours']/self.unit_hours) * 100

    def add_flavor_class_hours(self, flavor_class, unit_hours):
        if flavor_class not in self.by_flavor_class:
            self.by_flavor_class[flavor_class] = dict(count=0, unit_hours=0.0)
        cts = self.by_flavor_class[flavor_class]
        cts['count'] += 1
        cts['unit_hours'] += unit_hours
        cts['percent_count'] = (float(cts['count'])/self.count) * 100
        cts['percent_unit_hours'] = (cts['unit_hours']/self.unit_hours) * 100

    def add_flavor_hours(self, flavor, flavor_name, unit_hours):
        if flavor not in self.by_flavor:
            self.by_flavor[flavor] = dict(count=0, unit_hours=0.0)
        cts = self.by_flavor[flavor]
        cts['count'] += 1
        cts['unit_hours'] += unit_hours
        cts['percent_count'] = (float(cts['count'])/self.count) * 100
        cts['percent_unit_hours'] = (cts['unit_hours']/self.unit_hours) * 100
        cts['flavor_name'] = flavor_name

    def add_tenant_hours(self, tenant_info, unit_hours):
        tenant = tenant_info['tenant']
        cts = dict(count=0, unit_hours=0.0)
        for tname, tvalue in tenant_info['types'].items():
            if tvalue not in self.by_tenant[tname]:
                self.by_tenant[tname][tvalue] = dict()
            if tenant not in self.by_tenant[tname][tvalue]:
                self.by_tenant[tname][tvalue][tenant] = cts
            cts = self.by_tenant[tname][tvalue][tenant]
            cts[tname] = tvalue
        cts['count'] += 1
        cts['unit_hours'] += unit_hours
        cts['percent_count'] = (float(cts['count'])/self.count) * 100
        cts['percent_unit_hours'] = (cts['unit_hours']/self.unit_hours) * 100
        cts['tenant'] = tenant
        cts['account_name'] = tenant_info['account_name']

    def compile_hours(self):
        exists = self._get_verified_exists()
        self.count = exists.count()
        with self.tenant_manager as tenant_manager:
            for exist in exists:
                hours = self._get_instance_hours(exist)
                flavor, flavor_name, flavor_class, flavor_units = self._get_flavor_info(exist)
                tenant_info = tenant_manager.get_tenant_info(exist.tenant)
                unit_hours = hours * flavor_units
                self.unit_hours += unit_hours
                self.add_flavor_hours(flavor, flavor_name, unit_hours)
                self.add_flavor_class_hours(flavor_class, unit_hours)
                for tname, tvalue in tenant_info['types'].items():
                    self.add_type_hours(tname, tvalue, unit_hours)
                self.add_tenant_hours(tenant_info, unit_hours)

    def top_hundred(self, key):
        def th(d):
            top = dict()
            for t, customers in d.iteritems():
                top[t] = sorted(customers.values(), key=operator.itemgetter(key), reverse=True)[:100]
            return top
        top_hundred = dict()
        for type_name, tenants in self.by_tenant.iteritems():
            top_hundred[type_name] = th(tenants)
        return top_hundred

    def generate_json(self):
        report = dict(total_instance_count=self.count,
                      total_unit_hours=self.unit_hours,
                      flavor=self.by_flavor,
                      flavor_class=self.by_flavor_class,
                      top_hundred_by_count=self.top_hundred('count'),
                      top_hundred_by_unit_hours=self.top_hundred('unit_hours'))
        for ttype, stats in self.by_type.iteritems():
            report[ttype] = stats
        return json.dumps(report)

    def store(self, json_report):
        report = models.JsonReport(
                    json=json_report,
                    created=dt.dt_to_decimal(datetime.datetime.utcnow()),
                    period_start=self.start,
                    period_end=self.end,
                    version=1,
                    name='instance hours')
        report.save()


def valid_datetime(d):
    try:
        t = datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
        return t
    except Exception, e:
        raise argparse.ArgumentTypeError(
            "'%s' is not in YYYY-MM-DD HH:MM:SS format." % d)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('StackTach Instance Hours Report')
    parser.add_argument('--period_length',
                        choices=['hour', 'day'], default='day')
    parser.add_argument('--utcdatetime',
                        help="Override the end time used to generate report.",
                        type=valid_datetime, default=None)
    parser.add_argument('--store',
                        help="If set to true, report will be stored. "
                             "Otherwise, it will just be printed",
                        default=False, action="store_true")
    args = parser.parse_args()

    stacklog.set_default_logger_name('instance_hours')
    parent_logger = stacklog.get_logger('instance_hours', is_parent=True)
    log_listener = stacklog.LogListener(parent_logger)
    log_listener.start()

    tenant_manager = TenantManager()
    report = InstanceHoursReport(
                tenant_manager,
                time=args.utcdatetime,
                period_length=args.period_length)

    report.compile_hours()
    json = report.generate_json()

    if not args.store:
        print json
    else:
        report.store(json)
