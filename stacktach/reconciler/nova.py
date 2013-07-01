import json

import requests

from stacktach import utils as stackutils
from stacktach.reconciler import exceptions
from stacktach.reconciler.utils import empty_reconciler_instance


GET_INSTANCE_QUERY = "SELECT * FROM instances where uuid ='%s';"


class JSONBridgeClient(object):
    src_str = 'json_bridge:nova_db'

    def __init__(self, config):
        self.config = config

    def _url_for_region(self, region):
        return self.config['url'] + self.config['databases'][region]

    def _do_query(self, region, query):
        data = {'sql': query}
        credentials = (self.config['username'], self.config['password'])
        return requests.post(self._url_for_region(region), data,
                             verify=False, auth=credentials).json()

    def _to_reconciler_instance(self, instance):
        r_instance = empty_reconciler_instance()
        r_instance.update({
            'id': instance['uuid'],
            'instance_type_id': instance['instance_type_id'],
        })

        if instance['launched_at'] is not None:
            launched_at = stackutils.str_time_to_unix(instance['launched_at'])
            r_instance['launched_at'] = launched_at

        if instance['terminated_at'] is not None:
            deleted_at = stackutils.str_time_to_unix(instance['terminated_at'])
            r_instance['deleted_at'] = deleted_at

        if instance['deleted'] != 0:
            r_instance['deleted'] = True

        return r_instance

    def get_instance(self, region, uuid):
        results = self._do_query(region, GET_INSTANCE_QUERY % uuid)['result']
        if len(results) > 0:
            return self._to_reconciler_instance(results[0])
        else:
            msg = "Couldn't find instance (%s) using JSON Bridge in region (%s)"
            raise exceptions.NotFound(msg % (uuid, region))