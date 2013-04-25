from novaclient.v1_1 import client

from stacktach import models

reconciler_config = {
    'nova':{
        'DFW':{
            'username': 'm0lt3n',
            'project_id': '724740',
            'api_key': '',
            'auth_url': 'https://identity.api.rackspacecloud.com/v2.0',
            'auth_system': 'rackspace',
        },
        'ORD':{
            'username': 'm0lt3n',
            'project_id': '724740',
            'api_key': '',
            'auth_url': 'https://identity.api.rackspacecloud.com/v2.0',
            'auth_system': 'rackspace',
        },

    },
    'region_mapping_loc': '/etc/stacktach/region_mapping.json'
}

region_mapping = {
    'x': 'DFW'
}


class Reconciler(object):

    def __init__(self, config):
        self.config = reconciler_config
        self.region_mapping = region_mapping
        self.nova_clients = {}

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
        return self.region_mapping[str(raw.deployment.name)]

    def missing_exists_for_instance(self, launched_id,
                                    period_beginning,
                                    period_ending):
        launch = models.InstanceUsage.objects.get(id=launched_id)
        region = self._region_for_launch(launch)
        nova = self._get_nova(region)
        server = nova.servers.get(launch.instance)
