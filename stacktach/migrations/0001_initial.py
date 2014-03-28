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

# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Deployment'
        db.create_table(u'stacktach_deployment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'stacktach', ['Deployment'])

        # Adding model 'RawData'
        db.create_table(u'stacktach_rawdata', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('deployment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stacktach.Deployment'])),
            ('tenant', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('json', self.gf('django.db.models.fields.TextField')()),
            ('routing_key', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=20, null=True, blank=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=20, null=True, blank=True)),
            ('old_task', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=30, null=True, blank=True)),
            ('task', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=30, null=True, blank=True)),
            ('image_type', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, db_index=True)),
            ('when', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=6, db_index=True)),
            ('publisher', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=100, null=True, blank=True)),
            ('event', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('service', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('host', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=100, null=True, blank=True)),
            ('instance', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('request_id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal(u'stacktach', ['RawData'])

        # Adding model 'Lifecycle'
        db.create_table(u'stacktach_lifecycle', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('instance', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('last_state', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('last_task_state', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('last_raw', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stacktach.RawData'], null=True)),
        ))
        db.send_create_signal(u'stacktach', ['Lifecycle'])

        # Adding model 'InstanceUsage'
        db.create_table(u'stacktach_instanceusage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('instance', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('launched_at', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=20, decimal_places=6, db_index=True)),
            ('request_id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('instance_type_id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('tenant', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal(u'stacktach', ['InstanceUsage'])

        # Adding model 'InstanceDeletes'
        db.create_table(u'stacktach_instancedeletes', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('instance', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('launched_at', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=20, decimal_places=6, db_index=True)),
            ('deleted_at', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=20, decimal_places=6, db_index=True)),
            ('raw', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stacktach.RawData'], null=True)),
        ))
        db.send_create_signal(u'stacktach', ['InstanceDeletes'])

        # Adding model 'InstanceExists'
        db.create_table(u'stacktach_instanceexists', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('instance', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('launched_at', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=20, decimal_places=6, db_index=True)),
            ('deleted_at', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=20, decimal_places=6, db_index=True)),
            ('audit_period_beginning', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=20, decimal_places=6, db_index=True)),
            ('audit_period_ending', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=20, decimal_places=6, db_index=True)),
            ('message_id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('instance_type_id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=50, db_index=True)),
            ('fail_reason', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=300, null=True, blank=True)),
            ('raw', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['stacktach.RawData'])),
            ('usage', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['stacktach.InstanceUsage'])),
            ('delete', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['stacktach.InstanceDeletes'])),
            ('send_status', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, db_index=True)),
            ('tenant', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal(u'stacktach', ['InstanceExists'])

        # Adding model 'Timing'
        db.create_table(u'stacktach_timing', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50, db_index=True)),
            ('lifecycle', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stacktach.Lifecycle'])),
            ('start_raw', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['stacktach.RawData'])),
            ('end_raw', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['stacktach.RawData'])),
            ('start_when', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=20, decimal_places=6)),
            ('end_when', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=20, decimal_places=6)),
            ('diff', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=20, decimal_places=6, db_index=True)),
        ))
        db.send_create_signal(u'stacktach', ['Timing'])

        # Adding model 'RequestTracker'
        db.create_table(u'stacktach_requesttracker', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('request_id', self.gf('django.db.models.fields.CharField')(max_length=50, db_index=True)),
            ('lifecycle', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stacktach.Lifecycle'])),
            ('last_timing', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stacktach.Timing'], null=True)),
            ('start', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=6, db_index=True)),
            ('duration', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=6, db_index=True)),
            ('completed', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
        ))
        db.send_create_signal(u'stacktach', ['RequestTracker'])

        # Adding model 'JsonReport'
        db.create_table(u'stacktach_jsonreport', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('period_start', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('period_end', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('created', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=6, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50, db_index=True)),
            ('version', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('json', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'stacktach', ['JsonReport'])


    def backwards(self, orm):
        # Deleting model 'Deployment'
        db.delete_table(u'stacktach_deployment')

        # Deleting model 'RawData'
        db.delete_table(u'stacktach_rawdata')

        # Deleting model 'Lifecycle'
        db.delete_table(u'stacktach_lifecycle')

        # Deleting model 'InstanceUsage'
        db.delete_table(u'stacktach_instanceusage')

        # Deleting model 'InstanceDeletes'
        db.delete_table(u'stacktach_instancedeletes')

        # Deleting model 'InstanceExists'
        db.delete_table(u'stacktach_instanceexists')

        # Deleting model 'Timing'
        db.delete_table(u'stacktach_timing')

        # Deleting model 'RequestTracker'
        db.delete_table(u'stacktach_requesttracker')

        # Deleting model 'JsonReport'
        db.delete_table(u'stacktach_jsonreport')


    models = {
        u'stacktach.deployment': {
            'Meta': {'object_name': 'Deployment'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'stacktach.instancedeletes': {
            'Meta': {'object_name': 'InstanceDeletes'},
            'deleted_at': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'launched_at': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            'raw': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stacktach.RawData']", 'null': 'True'})
        },
        u'stacktach.instanceexists': {
            'Meta': {'object_name': 'InstanceExists'},
            'audit_period_beginning': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            'audit_period_ending': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            'delete': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['stacktach.InstanceDeletes']"}),
            'deleted_at': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            'fail_reason': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '300', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'instance_type_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'launched_at': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'raw': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['stacktach.RawData']"}),
            'send_status': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50', 'db_index': 'True'}),
            'tenant': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'usage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['stacktach.InstanceUsage']"})
        },
        u'stacktach.instanceusage': {
            'Meta': {'object_name': 'InstanceUsage'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'instance_type_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'launched_at': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            'request_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'tenant': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'stacktach.jsonreport': {
            'Meta': {'object_name': 'JsonReport'},
            'created': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'json': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'period_end': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'period_start': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'version': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        u'stacktach.lifecycle': {
            'Meta': {'object_name': 'Lifecycle'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'last_raw': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stacktach.RawData']", 'null': 'True'}),
            'last_state': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'last_task_state': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'stacktach.rawdata': {
            'Meta': {'object_name': 'RawData'},
            'deployment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stacktach.Deployment']"}),
            'event': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'db_index': 'True'}),
            'instance': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'json': ('django.db.models.fields.TextField', [], {}),
            'old_state': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'old_task': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'publisher': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'request_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'routing_key': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'task': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'tenant': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'when': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'})
        },
        u'stacktach.requesttracker': {
            'Meta': {'object_name': 'RequestTracker'},
            'completed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'duration': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_timing': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stacktach.Timing']", 'null': 'True'}),
            'lifecycle': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stacktach.Lifecycle']"}),
            'request_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'start': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'})
        },
        u'stacktach.timing': {
            'Meta': {'object_name': 'Timing'},
            'diff': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            'end_raw': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['stacktach.RawData']"}),
            'end_when': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lifecycle': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stacktach.Lifecycle']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'start_raw': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['stacktach.RawData']"}),
            'start_when': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6'})
        }
    }

    complete_apps = ['stacktach']
