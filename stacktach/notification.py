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
from stacktach import utils
from stacktach import stacklog
from stacktach import image_type
from stacktach import db


class Notification(object):
    def __init__(self, body, deployment, routing_key, json):
        self.body = body
        self.request_id = body.get('_context_request_id', "")
        self.deployment = deployment
        self.routing_key = routing_key
        self.json = json
        self.payload = body.get('payload', {})
        self.publisher = self.body['publisher_id']
        self.event = self.body['event_type']


    @property
    def when(self):
        when = self.body.get('timestamp', None)
        if not when:
            when = self.body['_context_timestamp']  # Old way of doing it
        when = utils.str_time_to_unix(when)
        return when

    @property
    def service(self):
        parts = self.publisher.split('.')
        return parts[0]

    @property
    def host(self):
        host = None
        parts = self.publisher.split('.')
        if len(parts) > 1:
            host = ".".join(parts[1:])
        return host

    @property
    def tenant(self):
        tenant = self.body.get('_context_project_id', None)
        tenant = self.payload.get('tenant_id', tenant)
        return tenant

    @property
    def instance(self):
        # instance UUID's seem to hide in a lot of odd places.
        instance = self.payload.get('instance_id', None)
        instance = self.payload.get('instance_uuid', instance)
        if not instance:
            instance = self.payload.get('exception', {}).get('kwargs', {}).get('uuid')
        if not instance:
            instance = self.payload.get('instance', {}).get('uuid')
        return instance

    @property
    def message_id(self):
        return self.body.get('message_id', None)

    def save(self):
        return db.create_generic_rawdata(deployment=self.deployment,
                                         routing_key=self.routing_key,
                                         tenant=self.tenant,
                                         json=self.json,
                                         when=self.when,
                                         publisher=self.publisher,
                                         event=self.event,
                                         service=self.service,
                                         host=self.host,
                                         instance=self.instance,
                                         request_id=self.request_id,
                                         message_id=self.message_id)


class GlanceNotification(Notification):
    def __init__(self, body, deployment, routing_key, json):
        super(GlanceNotification, self).__init__(body, deployment,
                                                 routing_key, json)
        if isinstance(self.payload, dict):
            self.properties = self.payload.get('properties', {})
            self.image_type = image_type.get_numeric_code(self.payload)
            self.status = self.payload.get('status', None)
            self.uuid = self.payload.get('id', None)
            self.size = self.payload.get('size', None)
            created_at = self.payload.get('created_at', None)
            self.created_at = created_at and utils.str_time_to_unix(created_at)
        else:
            self.properties = {}
            self.image_type = None
            self.status = None
            self.uuid = None
            self.size = None
            self.created_at = None

    @property
    def owner(self):
        if isinstance(self.payload, dict):
            return self.payload.get('owner', None)
        else:
            return None

    @property
    def instance(self):
        return self.properties.get('instance_uuid', None)

    @property
    def deleted_at(self):
        deleted_at = self.body.get('deleted_at', None)

        if isinstance(self.payload, dict):
            deleted_at = deleted_at or self.payload.get('deleted_at', None)

        return deleted_at and utils.str_time_to_unix(deleted_at)

    def save(self):
        return db.create_glance_rawdata(deployment=self.deployment,
                                        routing_key=self.routing_key,
                                        owner=self.owner,
                                        json=self.json,
                                        when=self.when,
                                        publisher=self.publisher,
                                        event=self.event,
                                        service=self.service,
                                        host=self.host,
                                        instance=self.instance,
                                        request_id=self.request_id,
                                        image_type=self.image_type,
                                        status=self.status,
                                        uuid=self.uuid)

    def save_exists(self, raw):
        if isinstance(self.payload, dict):
            audit_period_beginning = self.payload.get(
                'audit_period_beginning', None)
            audit_period_beginning = audit_period_beginning and\
                utils.str_time_to_unix(audit_period_beginning)
            audit_period_ending = self.payload.get(
                'audit_period_ending', None)
            audit_period_ending = audit_period_ending and \
                utils.str_time_to_unix(audit_period_ending)
            message_id = self.message_id
            images = self.payload.get('images', [])
        else:
            stacklog.warn("Received exists with invalid payload "
                          "GlanceRawData(%s)" % raw.id)
            audit_period_beginning = None
            audit_period_ending = None
            images = []

        for image in images:
            created_at = image['created_at']
            created_at = created_at and utils.str_time_to_unix(created_at)
            uuid = image['id']
            deleted_at = image['deleted_at']
            deleted_at = deleted_at and utils.str_time_to_unix(deleted_at)

            if created_at:
                values = {
                    'uuid': uuid,
                    'audit_period_beginning': audit_period_beginning,
                    'audit_period_ending': audit_period_ending,
                    'owner': self.owner,
                    'size': image['size'],
                    'raw': raw,
                    'message_id': message_id
                }
                usage = db.get_image_usage(uuid=uuid)
                values['usage'] = usage
                values['created_at'] = created_at
                if deleted_at:
                    delete = db.get_image_delete(uuid=uuid)
                    values['delete'] = delete
                    values['deleted_at'] = deleted_at

                db.create_image_exists(**values)
            else:
                stacklog.warn("Ignoring exists without created_at. GlanceRawData(%s)"
                              % raw.id)

    def save_usage(self, raw):
        values = {
            'uuid': self.uuid,
            'created_at': self.created_at,
            'owner': self.owner,
            'size': self.size,
            'last_raw': raw
        }
        db.create_image_usage(**values)

    def save_delete(self, raw):
        values = {
            'uuid': self.uuid,
            'raw': raw,
            'deleted_at': self.deleted_at
        }
        db.create_image_delete(**values)


class NovaNotification(Notification):
    def __init__(self, body, deployment, routing_key, json):
        super(NovaNotification, self).__init__(body, deployment, routing_key,
                                               json)
        self.state = self.payload.get('state', '')
        self.old_state = self.payload.get('old_state', '')
        self.old_task = self.payload.get('old_task_state', '')
        self.task = self.payload.get('new_task_state', '')
        self.image_type = image_type.get_numeric_code(self.payload)
        image_meta = self.payload.get('image_meta', {})
        self.os_architecture = \
            image_meta.get('org.openstack__1__architecture', '')
        self.os_distro = image_meta.get('org.openstack__1__os_distro', '')
        self.os_version = image_meta.get('org.openstack__1__os_version', '')
        self.rax_options = image_meta.get('com.rackspace__1__options', '')
        self.instance_type_id = self.payload.get('instance_type_id', None)
        self.instance_flavor_id = self.payload.get('instance_flavor_id', None)
        self.new_instance_type_id = \
            self.payload.get('new_instance_type_id', None)
        self.launched_at = self.payload.get('launched_at', None)
        self.deleted_at = self.payload.get('deleted_at', None)
        self.terminated_at = self.payload.get('terminated_at', None)
        self.audit_period_beginning = self.payload.get(
            'audit_period_beginning', None)
        self.audit_period_ending = self.payload.get(
            'audit_period_ending', None)
        self.message = self.payload.get('message', None)
        # (TMaddox) bandwidth could be None in the payload.
        bandwidth = self.payload.get('bandwidth', {}) or {}
        bandwidth_public = bandwidth.get('public', {})
        self.bandwidth_public_out = bandwidth_public.get('bw_out', 0)

    @property
    def host(self):
        host = None
        parts = self.publisher.split('.')
        if len(parts) > 1:
            host = ".".join(parts[1:])
        return host

    @property
    def service(self):
        parts = self.publisher.split('.')
        return parts[0]

    def save(self):
        return db.create_nova_rawdata(deployment=self.deployment,
                                      routing_key=self.routing_key,
                                      tenant=self.tenant,
                                      json=self.json,
                                      when=self.when,
                                      publisher=self.publisher,
                                      event=self.event,
                                      service=self.service,
                                      host=self.host,
                                      instance=self.instance,
                                      request_id=self.request_id,
                                      image_type=self.image_type,
                                      state=self.state,
                                      old_state=self.old_state,
                                      task=self.task,
                                      old_task=self.old_task,
                                      os_architecture=self.os_architecture,
                                      os_distro=self.os_distro,
                                      os_version=self.os_version,
                                      rax_options=self.rax_options)


def notification_factory(body, deployment, routing_key, json, exchange):
    if exchange == 'nova':
        return NovaNotification(body, deployment, routing_key, json)
    if exchange == "glance":
        return GlanceNotification(body, deployment, routing_key, json)
    return Notification(body, deployment, routing_key, json)
