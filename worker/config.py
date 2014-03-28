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


import json
import os

config_filename = os.environ.get('STACKTACH_DEPLOYMENTS_FILE',
                                 'stacktach_worker_config.json')
try:
    from local_settings import *
    config_filename = STACKTACH_DEPLOYMENTS_FILE
except ImportError:
    pass

config = None
with open(config_filename, "r") as f:
    config = json.load(f)


def deployments():
    return config['deployments']


def topics():
    return config['topics']
