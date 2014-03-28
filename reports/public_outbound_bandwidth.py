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
import datetime
import json
import logging
import os
import sys

sys.path.append(os.environ.get('STACKTACH_INSTALL_DIR', '/stacktach'))

from stacktach import datetime_to_decimal as dt
from stacktach import models

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def __get_previous_period(time):
    last_period = time - datetime.timedelta(days=1)
    start = datetime.datetime(year=last_period.year,
                              month=last_period.month,
                              day=last_period.day)
    end = datetime.datetime(year=time.year,
                            month=time.month,
                            day=time.day)
    return start, end


def __get_instance_exists(beginning, ending):
    filters = {
        'audit_period_beginning__gte': beginning,
        'audit_period_ending__lte': ending,
    }
    return models.InstanceExists.objects.filter(**filters)


def __audit_for_instance_exists(beginning, ending):
    beginning_decimal = dt.dt_to_decimal(beginning)
    ending_decimal = dt.dt_to_decimal(ending)
    instance_exists = __get_instance_exists(beginning_decimal, ending_decimal)
    total_bw = reduce(lambda x, y: x + y.bandwidth_public_out, instance_exists,
                      0)
    report = {
        'total_public_outbound_bandwidth': total_bw,
    }

    return report


def __store_report_in_db(start, end, report):
    values = {
        'json': __make_json_report(report),
        'created': dt.dt_to_decimal(datetime.datetime.utcnow()),
        'period_start': start,
        'period_end': end,
        'version': 1,
        'name': 'public outbound bandwidth'
    }

    report = models.JsonReport(**values)
    report.save()


def __make_json_report(report):
    return json.dumps(report)


if __name__ == '__main__':
    start, end = __get_previous_period(datetime.datetime.utcnow())
    logger.debug("Aggregating bw usage for period: %s to %s" % (start, end))
    report = __audit_for_instance_exists(start, end)
    __store_report_in_db(start, end, report)

