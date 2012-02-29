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


class Tenant(models.Model):
    email = models.CharField(max_length=50)
    project_name = models.CharField(max_length=50)
    nova_stats_template = models.CharField(max_length=200)
    loggly_template = models.CharField(max_length=200)
    tenant_id = models.AutoField(primary_key=True, unique=True)


class RawData(models.Model):
    tenant = models.ForeignKey(Tenant, db_index=True,
                               to_field='tenant_id')
    nova_tenant = models.CharField(max_length=50, null=True,
                                   blank=True, db_index=True)
    json = models.TextField()
    routing_key = models.CharField(max_length=50, null=True,
                                   blank=True, db_index=True)
    state = models.CharField(max_length=50, null=True,
                             blank=True, db_index=True)
    when = models.DateTimeField(db_index=True)
    microseconds = models.IntegerField(default=0)
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


class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ('email', 'project_name', 'nova_stats_template', 'loggly_template')
