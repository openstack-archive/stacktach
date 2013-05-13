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

from novaclient.exceptions import NotFound
from novaclient.v1_1 import client

from stacktach import models
from stacktach import utils

TERMINATED_AT_KEY = 'OS-INST-USG:terminated_at'


class Reconciler(object):

    def __init__(self, config, region_mapping=None):
        self.config = config
        self.region_mapping = (region_mapping or
                               Reconciler._load_region_mapping(config))
        self.nova_clients = {}

    @classmethod
    def _load_region_mapping(cls, config):
        with open(config['region_mapping_loc']) as f:
            return json.load(f)

    def _get_nova(self, region):
        if region in self.nova_clients:
            return self.nova_clients[region]

        region_cfg = self.config['nova'][region]
        region_auth_system = region_cfg.get('auth_system', 'keystone')

        nova = client.Client(region_cfg['username'], region_cfg['api_key'],
                             region_cfg['project_id'],
                             auth_url=region_cfg['auth_url'],
                             auth_system=region_auth_system)

        self.nova_clients[region] = nova
        return nova

    def _region_for_launch(self, launch):
        request = launch.request_id
        raws = models.RawData.objects.filter(request_id=request)
        if raws.count() == 0:
            return False
        raw = raws[0]
        deployment_name = str(raw.deployment.name)
        if deployment_name in self.region_mapping:
            return self.region_mapping[deployment_name]
        else:
            return False

    def _reconcile_from_api(self, launch, server):
        terminated_at = server._info[TERMINATED_AT_KEY]
        terminated_at = utils.str_time_to_unix(terminated_at)
        values = {
            'instance': server.id,
            'launched_at': launch.launched_at,
            'deleted_at': terminated_at,
            'instance_type_id': launch.instance_type_id,
            'source': 'reconciler:nova_api',
        }
        models.InstanceReconcile(**values).save()

    def _reconcile_from_api_not_found(self, launch):
        values = {
            'instance': launch.instance,
            'launched_at': launch.launched_at,
            'deleted_at': 1,
            'instance_type_id': launch.instance_type_id,
            'source': 'reconciler:nova_api:not_found',
        }
        models.InstanceReconcile(**values).save()

    def missing_exists_for_instance(self, launched_id,
                                    period_beginning):
        reconciled = False
        launch = models.InstanceUsage.objects.get(id=launched_id)
        region = self._region_for_launch(launch)
        nova = self._get_nova(region)
        try:
            server = nova.servers.get(launch.instance)
            if (server.status == 'DELETED' and
                    TERMINATED_AT_KEY in server._info):
                # Check to see if instance has been deleted
                terminated_at = server._info[TERMINATED_AT_KEY]
                terminated_at = utils.str_time_to_unix(terminated_at)

                if terminated_at < period_beginning:
                    # Check to see if instance was deleted before period.
                    # If so, we shouldn't expect an exists.
                    self._reconcile_from_api(launch, server)
                    reconciled = True
        except NotFound:
            self._reconcile_from_api_not_found(launch)
            reconciled = True

        return reconciled
