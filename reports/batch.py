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

# This is a one-time utility script for backfilling reports.
# Be sure to set up your DJANGO_SETTINGS_MODULE env var first.

import datetime
import subprocess

start_date =  datetime.date(2013, 2, 17)

today = datetime.datetime.now().date()
target = today - datetime.timedelta(days=30)

done = today - start_date
days = done.days

while start_date != target:
    for region in ["dfw", "lon", "ord"]:
        cmd = "python pretty.py --utcdate %s --region %s  --store --percentile 97" % (start_date, region)
        print cmd
        subprocess.call(cmd, shell=True)

    start_date = start_date - datetime.timedelta(days=1)
