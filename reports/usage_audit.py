import datetime
from django.db.models import F
from stacktach import models


def _status_queries(exists_query):
    verified = exists_query.filter(status=models.InstanceExists.VERIFIED)
    reconciled = exists_query.filter(status=models.InstanceExists.RECONCILED)
    fail = exists_query.filter(status=models.InstanceExists.FAILED)
    pending = exists_query.filter(status=models.InstanceExists.PENDING)
    verifying = exists_query.filter(status=models.InstanceExists.VERIFYING)

    return verified, reconciled, fail, pending, verifying


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
     fail, pending, verifying) = _status_queries(exists_query)

    (success, unsent, redirect,
     client_error, server_error) = _send_status_queries(verified)

    report = {
        'count': exists_query.count(),
        'verified': verified.count(),
        'reconciled': reconciled.count(),
        'failed': fail.count(),
        'pending': pending.count(),
        'verifying': verifying.count(),
        'send_status': {
            'success': success.count(),
            'unsent': unsent.count(),
            'redirect': redirect.count(),
            'client_error': client_error.count(),
            'server_error': server_error.count(),
        }
    }

    return report


def _verifier_audit_for_day(beginning, ending, exists_model):
    summary = {}

    filters = {
        'raw__when__gte': beginning,
        'raw__when__lte': ending,
        'audit_period_ending': F('audit_period_beginning') + (60*60*24)
    }
    periodic_exists = exists_model.objects.filter(**filters)

    summary['periodic'] = _audit_for_exists(periodic_exists)

    filters = {
        'raw__when__gte': beginning,
        'raw__when__lte': ending,
        'audit_period_ending__lt': F('audit_period_beginning') + (60*60*24)
    }
    instant_exists = exists_model.objects.filter(**filters)

    summary['instantaneous'] = _audit_for_exists(instant_exists)

    filters = {
        'raw__when__gte': beginning,
        'raw__when__lte': ending,
        'status': exists_model.FAILED
    }
    failed = exists_model.objects.filter(**filters)
    detail = []
    for exist in failed:
        detail.append(['Exist', exist.id, exist.fail_reason])
    return summary, detail

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