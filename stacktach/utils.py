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
import uuid

from stacktach import datetime_to_decimal as dt


def str_time_to_unix(when):
    if 'Z' in when:
        when = _try_parse(when, ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"])
    elif 'T' in when:
        when = _try_parse(when, ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"])
    else:
        when = _try_parse(when, ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"])

    return dt.dt_to_decimal(when)


def _try_parse(when, formats):
    last_exception = None
    for format in formats:
        try:
            when = datetime.datetime.strptime(when, format)
            parsed = True
        except Exception, e:
            parsed = False
            last_exception = e
        if parsed:
            return when
    print "Bad DATE ", last_exception


def is_uuid_like(val):
    try:
        converted = str(uuid.UUID(val))
        if '-' not in val:
            converted = converted.replace('-', '')
        return converted == val
    except (TypeError, ValueError, AttributeError):
        return False


def is_request_id_like(val):
    if val[0:4] == 'req-':
        val = val[4:]
    return is_uuid_like(val)


def get_local_mysqldb_connection():
    import os

    try:
        db_engine = STACKTACH_DB_ENGINE
        db_name = STACKTACH_DB_NAME
        db_host = STACKTACH_DB_HOST
        db_username = STACKTACH_DB_USERNAME
        db_password = STACKTACH_DB_PASSWORD
        db_port = STACKTACH_DB_PORT
        install_dir = os.path.expanduser(STACKTACH_INSTALL_DIR)
    except ImportError:
        db_engine = os.environ.get('STACKTACH_DB_ENGINE',
                                   'django.db.backends.mysql')
        db_name = os.environ['STACKTACH_DB_NAME']
        db_host = os.environ.get('STACKTACH_DB_HOST', "")
        db_username = os.environ['STACKTACH_DB_USERNAME']
        db_password = os.environ['STACKTACH_DB_PASSWORD']
        db_port = os.environ.get('STACKTACH_DB_PORT', "")
        install_dir = os.environ['STACKTACH_INSTALL_DIR']

    connection_obj = MySQLdb.connect(user=db_username, host=db_host, passwd=db_password, port=int(db_port), db=db_name)
    return connection_obj
