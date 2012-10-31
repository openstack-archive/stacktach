# Copyright 2012 - Dark Secret Software Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from django import forms
from django.db import models


class Deployment(models.Model):
    name = models.CharField(max_length=50)


def get_or_create_deployment(name):
    return Deployment.objects.get_or_create(name=name)


class RawData(models.Model):
    deployment = models.ForeignKey(Deployment)
    tenant = models.CharField(max_length=50, null=True, blank=True,
                              db_index=True)
    json = models.TextField()
    routing_key = models.CharField(max_length=50, null=True,
                                   blank=True, db_index=True)
    state = models.CharField(max_length=20, null=True,
                             blank=True, db_index=True)
    old_state = models.CharField(max_length=20, null=True,
                             blank=True, db_index=True)
    old_task = models.CharField(max_length=30, null=True,
                             blank=True, db_index=True)
    when = models.DecimalField(max_digits=20, decimal_places=6)
    publisher = models.CharField(max_length=100, null=True,
                                 blank=True, db_index=True)
    event = models.CharField(max_length=50, null=True,
                                 blank=True, db_index=True)
    service = models.CharField(max_length=50, null=True,
                                 blank=True, db_index=True)
    host = models.CharField(max_length=100, null=True,
                                 blank=True, db_index=True)
    instance = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)
    request_id = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)

    def __repr__(self):
        return self.event


class Lifecycle(models.Model):
    instance = models.CharField(max_length=50, null=True,
                                blank=True, db_index=True)
    last_state = models.CharField(max_length=50, null=True,
                             blank=True, db_index=True)
    last_task_state = models.CharField(max_length=50, null=True,
                             blank=True, db_index=True)
    last_raw = models.ForeignKey(RawData, null=True)


class Timing(models.Model):
    name = models.CharField(max_length=50, db_index=True)
    lifecycle = models.ForeignKey(Lifecycle)
    start_raw = models.ForeignKey(RawData, related_name='+', null=True)
    end_raw = models.ForeignKey(RawData, related_name='+', null=True)

    start_when = models.DecimalField(null=True, max_digits=20, decimal_places=6)
    end_when = models.DecimalField(null=True, max_digits=20, decimal_places=6)

    diff = models.DecimalField(null=True, max_digits=20, decimal_places=6)
