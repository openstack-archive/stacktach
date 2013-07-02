# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'GlanceRawData'
        db.create_table(u'stacktach_glancerawdata', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('deployment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stacktach.Deployment'])),
            ('owner', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=255, null=True, blank=True)),
            ('json', self.gf('django.db.models.fields.TextField')()),
            ('routing_key', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('when', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=6, db_index=True)),
            ('publisher', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=100, null=True, blank=True)),
            ('event', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('service', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('host', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=100, null=True, blank=True)),
            ('instance', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('request_id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('uuid', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=36, null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, db_index=True)),
            ('image_type', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, db_index=True)),
        ))
        db.send_create_signal(u'stacktach', ['GlanceRawData'])

        # Adding model 'GenericRawData'
        db.create_table(u'stacktach_genericrawdata', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('deployment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stacktach.Deployment'])),
            ('tenant', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('json', self.gf('django.db.models.fields.TextField')()),
            ('routing_key', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('image_type', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, db_index=True)),
            ('when', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=6, db_index=True)),
            ('publisher', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=100, null=True, blank=True)),
            ('event', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('service', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('host', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=100, null=True, blank=True)),
            ('instance', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('request_id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal(u'stacktach', ['GenericRawData'])


    def backwards(self, orm):
        # Deleting model 'GlanceRawData'
        db.delete_table(u'stacktach_glancerawdata')

        # Deleting model 'GenericRawData'
        db.delete_table(u'stacktach_genericrawdata')


    models = {
        u'stacktach.deployment': {
            'Meta': {'object_name': 'Deployment'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'stacktach.genericrawdata': {
            'Meta': {'object_name': 'GenericRawData'},
            'deployment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stacktach.Deployment']"}),
            'event': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'db_index': 'True'}),
            'instance': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'json': ('django.db.models.fields.TextField', [], {}),
            'publisher': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'request_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'routing_key': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'tenant': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'when': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'})
        },
        u'stacktach.glancerawdata': {
            'Meta': {'object_name': 'GlanceRawData'},
            'deployment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stacktach.Deployment']"}),
            'event': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'db_index': 'True'}),
            'instance': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'json': ('django.db.models.fields.TextField', [], {}),
            'owner': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'publisher': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'request_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'routing_key': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'db_index': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'when': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'})
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
            'os_architecture': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'os_distro': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'os_version': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'raw': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['stacktach.RawData']"}),
            'rax_options': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'send_status': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '50', 'db_index': 'True'}),
            'tenant': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'usage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['stacktach.InstanceUsage']"})
        },
        u'stacktach.instancereconcile': {
            'Meta': {'object_name': 'InstanceReconcile'},
            'deleted_at': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'instance_type_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'launched_at': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            'row_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'row_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        u'stacktach.instanceusage': {
            'Meta': {'object_name': 'InstanceUsage'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'instance_type_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'launched_at': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '6', 'db_index': 'True'}),
            'os_architecture': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'os_distro': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'os_version': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'rax_options': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
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
        u'stacktach.rawdataimagemeta': {
            'Meta': {'object_name': 'RawDataImageMeta'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'os_architecture': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'os_distro': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'os_version': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'raw': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stacktach.RawData']"}),
            'rax_options': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
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