# Copyright (c) 2012 - Rackspace Inc.
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
    def __init__(self, field_name, expected, actual, uuid):
        self.field_name = field_name
        self.expected = expected
        self.actual = actual
        self.reason = \
            "Failed at {failed_at} UTC for {uuid}: Expected {field_name} " \
            "to be '{expected}' got '{actual}'".\
            format(failed_at=datetime.datetime.utcnow(), uuid=uuid,
                   field_name=field_name, expected=expected,
                   actual=actual)


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
        self.field_name = field_name
        self.reason = \
            "Failed at {failed_at} UTC for {uuid}: " \
            "{{{field_name}: {value}}} was of incorrect type for " \
            "exist id {exist_id}".format(
                failed_at=datetime.datetime.utcnow(), uuid=uuid,
                field_name=field_name, value=value, exist_id=exist_id)

