# Copyright 2012 Openstack LLC.
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

# This is a sample conf file. Use it as a guide to make your own

DEPLOYMENTS = [
    # My fun conf
    dict(
        tenant_id=1,  # This is the stacktach tenant, not an openstack tenant
        name="my-fun-nova-deploy",
        url='http://stacktach.my-fun-nova-deploy.com', # The url for the base of the django app
        rabbit_host="1.2.3.4",  # ip/host name of the amqp server to listen to
        rabbit_port=5672,
        rabbit_userid="amqp-user-1",
        rabbit_password="some secret password",
        rabbit_virtual_host="amqp-vhost"),
]
