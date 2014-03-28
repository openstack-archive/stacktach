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
import calendar
import datetime
import decimal


def dt_to_decimal(utc):
    decimal.getcontext().prec = 30
    return decimal.Decimal(str(calendar.timegm(utc.utctimetuple()))) + \
           (decimal.Decimal(str(utc.microsecond)) /
           decimal.Decimal("1000000.0"))


def dt_from_decimal(dec):
    if dec == None:
        return "n/a"
    integer = int(dec)
    micro = (dec - decimal.Decimal(integer)) * decimal.Decimal(1000000)

    daittyme = datetime.datetime.utcfromtimestamp(integer)
    return daittyme.replace(microsecond=micro)


def sec_to_str(sec):
    sec = int(sec)
    if sec < 60:
        return "%ds" % sec
    minutes = sec / 60
    sec = sec % 60
    if minutes < 60:
        return "%d:%02ds" % (minutes, sec)
    hours = minutes / 60
    minutes = minutes % 60
    return "%02d:%02d:%02d" % (hours, minutes, sec)
