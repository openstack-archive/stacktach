from stacktach import utils
from stacktach import image_type


class Notification(object):
    def __init__(self, body):
        self.body = body
        self.request_id = body['_context_request_id']
        self.payload = body.get('payload', {})
        self.state = self.payload.get('state', "")
        self.old_state = self.payload.get('old_state', "")
        self.old_task = self.payload.get('old_task_state', "")
        self.task = self.payload.get('new_task_state', "")
        self.image_type = image_type.get_numeric_code(self.payload)
        self.os_architecture = self.payload['image_meta']['org.openstack__1__architecture']
        self.os_distro = self.payload['image_meta']['org.openstack__1__os_distro']
        self.os_version = self.payload['image_meta']['org.openstack__1__os_version']
        self.rax_options = self.payload['image_meta']['com.rackspace__1__options']

    @property
    def when(self):
        when = self.body.get('timestamp', None)
        if not when:
            when = self.body['_context_timestamp']  # Old way of doing it
        when = utils.str_time_to_unix(when)
        return when

    def rawdata_kwargs(self, deployment, routing_key, json):
        return {
            'deployment': deployment,
            'routing_key': routing_key,
            'event': self.event,
            'publisher': self.publisher,
            'json': json,
            'state': self.state,
            'old_state': self.old_state,
            'task': self.task,
            'old_task': self.old_task,
            'image_type': self.image_type,
            'when': self.when,
            'publisher': self.publisher,
            'service': self.service,
            'host': self.host,
            'instance': self.instance,
            'request_id': self.request_id,
            'tenant': self.tenant,
            'os_architecture': self.os_architecture,
            'os_distro': self.os_distro,
            'os_version': self.os_version,
            'rax_options': self.rax_options
        }

from stacktach.notification import Notification


class ComputeUpdateNotification(Notification):
    def __init__(self, body):
        super(ComputeUpdateNotification, self).__init__(body)

    @property
    def instance(self):
        return None

    @property
    def host(self):
        return self.body['args']['host']

    @property
    def publisher(self):
        return None

    @property
    def service(self):
        return self.body['args']['service_name']

    @property
    def event(self):
        return self.body['method']

    @property
    def tenant(self):
        return self.body['args'].get('_context_project_id', None)


class MonitorNotification(Notification):
    def __init__(self, body):
        super(MonitorNotification, self).__init__(body)

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
    def host(self):
        host = None
        parts = self.publisher.split('.')
        if len(parts) > 1:
            host = ".".join(parts[1:])
        return host

    @property
    def publisher(self):
        return self.body['publisher_id']

    @property
    def service(self):
        parts = self.publisher.split('.')
        return parts[0]

    @property
    def event(self):
        return self.body['event_type']

    @property
    def tenant(self):
        tenant = self.body.get('_context_project_id', None)
        tenant = self.payload.get('tenant_id', tenant)
        return tenant
