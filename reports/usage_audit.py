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
from django.db.models import F
from django.db.models import Q
from stacktach import models


def _status_queries(exists_query):
    verified = exists_query.filter(status=models.InstanceExists.VERIFIED)
    reconciled = exists_query.filter(status=models.InstanceExists.RECONCILED)
    fail = exists_query.filter(status=models.InstanceExists.FAILED)
    pending = exists_query.filter(status=models.InstanceExists.PENDING)
    verifying = exists_query.filter(status=models.InstanceExists.VERIFYING)
    sent_unverified = exists_query.filter(status=models.InstanceExists.SENT_UNVERIFIED)
    sent_failed = exists_query.filter(status=models.InstanceExists.VERIFYING)
    sent_verifying = exists_query.filter(status=models.InstanceExists.SENT_VERIFYING)
    return verified, reconciled, fail, pending, verifying, sent_unverified, \
        sent_failed, sent_verifying


def _send_status_queries(exists_query):
    unsent = exists_query.filter(send_status=0)
    success = exists_query.filter(send_status__gte=200,
                                  send_status__lt=300)
    redirect = exists_query.filter(send_status__gte=300,
                                   send_status__lt=400)
    client_error = exists_query.filter(send_status__gte=400,
                                       send_status__lt=500)
    server_error = exists_query.filter(send_status__gte=500,
                                       send_status__lt=600)
    return success, unsent, redirect, client_error, server_error


def _audit_for_exists(exists_query):
    (verified, reconciled,
     fail, pending, verifying, sent_unverified,
     sent_failed, sent_verifying) = _status_queries(exists_query)

    (success, unsent, redirect,
     client_error, server_error) = _send_status_queries(verified)

    (success_rec, unsent_rec, redirect_rec,
     client_error_rec, server_error_rec) = _send_status_queries(reconciled)

    report = {
        'count': exists_query.count(),
        'verified': verified.count(),
        'reconciled': reconciled.count(),
        'failed': fail.count(),
        'pending': pending.count(),
        'verifying': verifying.count(),
        'sent_unverified': sent_unverified.count(),
        'sent_failed': sent_failed.count(),
        'sent_verifying': sent_verifying.count(),
        'send_status': {
            'success': success.count(),
            'unsent': unsent.count(),
            'redirect': redirect.count(),
            'client_error': client_error.count(),
            'server_error': server_error.count(),
        },
        'send_status_rec': {
            'success': success_rec.count(),
            'unsent': unsent_rec.count(),
            'redirect': redirect_rec.count(),
            'client_error': client_error_rec.count(),
            'server_error': server_error_rec.count(),
        }
    }

    return report


def _verified_audit_base(base_query, exists_model):
    summary = {}

    periodic_range = Q(audit_period_ending=(F('audit_period_beginning') +
                                            (60*60*24)))
    periodic_exists = exists_model.objects.filter(base_query & periodic_range)
    summary['periodic'] = _audit_for_exists(periodic_exists)

    instant_range = Q(audit_period_ending__lt=(F('audit_period_beginning') +
                                               (60*60*24)))
    instant_exists = exists_model.objects.filter(base_query & instant_range)
    summary['instantaneous'] = _audit_for_exists(instant_exists)

    failed_query = Q(status=exists_model.FAILED)
    failed = exists_model.objects.filter(base_query & failed_query)
    detail = [['Exist', e.id, e.fail_reason] for e in failed]
    return summary, detail


def _verifier_audit_for_day(beginning, ending, exists_model):
    base_query = Q(raw__when__gte=beginning, raw__when__lte=ending)
    return _verified_audit_base(base_query, exists_model)


def _verifier_audit_for_day_ums(beginning, ending, exists_model, ums_offset=0):
    # NOTE(apmelton):
    # This is the UMS query we're trying to match.
    # where (
    #     (created_date between sysdate-1||'12.00.00.000000000 AM' and
    #                           sysdate-1||'04.00.00.000000000 AM' and
    #      audit_period_begin_timestamp >= sysdate-1||'12.00.00.000000000 AM')
    # OR (created_date > sysdate-1||'04.00.00.000000000 AM' and
    #     audit_period_begin_timestamp < sysdate||'12.00.00.000000000 AM' ))
    ums = (Q(raw__when__gte=beginning, raw__when__lte=beginning + ums_offset,
             audit_period_beginning__gte=beginning) |
           Q(raw__when__gt=beginning + ums_offset,
             audit_period_beginning__lt=ending))

    return _verified_audit_base(ums, exists_model)


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
