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

import json

from stacktach import models
from stacktach.reconciler import exceptions
from stacktach.reconciler import nova
from stacktach import stacklog

DEFAULT_CLIENT = nova.JSONBridgeClient

CONFIG = {
    'client_class': 'JSONBridgeClient',
    'client': {
        'url': 'http://stack.dev.ramielrowe.com:8080/query/',
        'username': '',
        'password': '',
        'databases': {
            'RegionOne': 'nova',
        }
    },
    'region_mapping_loc': '/etc/stacktach/region_mapping.json'
}


class Reconciler(object):

    def __init__(self, config, client=None, region_mapping=None):
        self.config = config
        self.client = (client or Reconciler.load_client(config))
        self.region_mapping = (region_mapping or
                               Reconciler.load_region_mapping(config))

    @classmethod
    def load_client(cls, config):
        client_class = config.get('client_class')
        if client_class == 'JSONBridgeClient':
            return nova.JSONBridgeClient(config['client'])
        else:
            return DEFAULT_CLIENT(config['client'])

    @classmethod
    def load_region_mapping(cls, config):
        with open(config['region_mapping_loc']) as f:
            return json.load(f)

    def _region_for_usage(self, usage):
        deployment = usage.deployment()
        if deployment:
            deployment_name = str(deployment.name)
            if deployment_name in self.region_mapping:
                return self.region_mapping[deployment_name]
            else:
                return False
        else:
            return False

    def _reconcile_instance(self, usage, src, deleted_at=None):
        values = {
            'instance': usage.instance,
            'launched_at': usage.launched_at,
            'deleted_at': deleted_at,
            'instance_type_id': usage.instance_type_id,
            'source': 'reconciler:%s' % src,
            'tenant': usage.tenant,
            'os_architecture': usage.os_architecture,
            'os_distro': usage.os_distro,
            'os_version': usage.os_version,
            'rax_options': usage.rax_options,
        }
        models.InstanceReconcile(**values).save()

    def _fields_match(self, exists, instance):
        match_code = 0

        if (exists.launched_at != instance['launched_at'] or
                exists.instance_type_id != instance['instance_type_id'] or
                exists.tenant != instance['tenant'] or
                exists.os_architecture != instance['os_architecture'] or
                exists.os_distro != instance['os_distro'] or
                exists.os_version != instance['os_version'] or
                exists.rax_options != instance['rax_options']):
            match_code = 1

        if exists.deleted_at is not None:
            # Exists says deleted
            if (instance['deleted'] and
                    exists.deleted_at != instance['deleted_at']):
                # Nova says deleted, but times don't match
                match_code = 2
            elif not instance['deleted']:
                # Nova says not deleted
                match_code = 3
        elif exists.deleted_at is None and instance['deleted']:
            # Exists says not deleted, but Nova says deleted
            match_code = 4

        return match_code

    def missing_exists_for_instance(self, launched_id,
                                    period_beginning):
        reconciled = False
        launch = models.InstanceUsage.objects.get(id=launched_id)
        region = self._region_for_usage(launch)
        try:
            instance = self.client.get_instance(region, launch.instance)
            if instance['deleted'] and instance['deleted_at'] is not None:
                # Check to see if instance has been deleted
                deleted_at = instance['deleted_at']

                if deleted_at < period_beginning:
                    # Check to see if instance was deleted before period.
                    # If so, we shouldn't expect an exists.
                    self._reconcile_instance(launch, self.client.src_str,
                                             deleted_at=instance['deleted_at'])
                    reconciled = True
        except exceptions.NotFound:
            stacklog.info("Couldn't find instance for launch %s" % launched_id)

        return reconciled

    def failed_validation(self, exists):
        reconciled = False
        region = self._region_for_usage(exists)
        try:
            instance = self.client.get_instance(region, exists.instance,
                                                get_metadata=True)
            match_code = self._fields_match(exists, instance)
            if match_code == 0:
                self._reconcile_instance(exists, self.client.src_str,
                                         deleted_at=exists.deleted_at)
                reconciled = True
            else:
                msg = "Exists %s failed reconciliation with code %s"
                msg %= (exists.id, match_code)
                stacklog.info(msg)
        except exceptions.NotFound:
            stacklog.info("Couldn't find instance for exists %s" % exists.id)

        return reconciled
