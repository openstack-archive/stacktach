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


class VerificationException(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason


class NotFound(VerificationException):
    def __init__(self, object_type, search_params):
        self.object_type = object_type
        self.search_params = search_params
        self.reason = "Couldn't find %s using %s" % (self.object_type,
                                                     self.search_params)


class AmbiguousResults(VerificationException):
    def __init__(self, object_type, search_params):
        self.object_type = object_type
        self.search_params = search_params
        msg = "Ambiguous results for %s using %s" % (self.object_type,
                                                     self.search_params)
        self.reason = msg


class FieldMismatch(VerificationException):
    def __init__(self, field_name, entity_1, entity_2, uuid):
        #instance fields for testing ease
        self.field_name = field_name
        self.entity_1 = entity_1
        self.entity_2 = entity_2
        self.uuid = uuid

        self.reason = \
            "Failed at {failed_at} UTC for {uuid}: Data mismatch for " \
            "'{field_name}' - '{name_1}' contains '{value_1}' but '{name_2}' " \
            "contains '{value_2}'".\
            format(failed_at=datetime.datetime.utcnow(), uuid=self.uuid,
                   field_name=self.field_name, name_1=entity_1['name'],
                   value_1=self.entity_1['value'],
                   name_2=self.entity_2['name'],
                   value_2=self.entity_2['value'])


class NullFieldException(VerificationException):
    def __init__(self, field_name, exist_id, uuid):
        self.field_name = field_name
        self.reason = \
            "Failed at {failed_at} UTC for {uuid}: {field_name} field " \
            "was null for exist id {exist_id}".format(
                failed_at=datetime.datetime.utcnow(), uuid=uuid,
                field_name=field_name, exist_id=exist_id)


class WrongTypeException(VerificationException):
    def __init__(self, field_name, value, exist_id, uuid):
        #made instance fields to ease testing
        self.field_name = field_name
        self.value = value
        self.exist_id = exist_id
        self.uuid = uuid

        self.reason = \
            "Failed at {failed_at} UTC for {uuid}: " \
            "{{{field_name}: {value}}} was of incorrect type for " \
            "exist id {exist_id}".format(
                failed_at=datetime.datetime.utcnow(), uuid=self.uuid,
                field_name=self.field_name, value=self.value,
                exist_id=self.exist_id)
