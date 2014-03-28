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
import os
import re
import sys
import unittest


def setup_sys_path():
    sys.path = [os.path.abspath(os.path.dirname('stacktach'))] + sys.path


def setup_environment():
    '''Other than the settings module, these config settings just need
        to have values. The are used when the settings module is loaded
        and then never again.'''
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    os.environ['STACKTACH_DB_ENGINE'] = ''
    os.environ['STACKTACH_DB_NAME'] = ''
    os.environ['STACKTACH_DB_HOST'] = ''
    os.environ['STACKTACH_DB_USERNAME'] = ''
    os.environ['STACKTACH_DB_PASSWORD'] = ''
    os.environ['STACKTACH_INSTALL_DIR'] = ''


setup_sys_path()
setup_environment()

from stacktach import stacklog

stacklog.set_default_logger_location("/tmp/%s.log")
default_logger = stacklog.get_logger()
worker_logger = stacklog.get_logger('worker')
verifier_logger = stacklog.get_logger('verifier')


class _AssertRaisesContext(object):
    """A context manager used to implement TestCase.assertRaises* methods."""

    def __init__(self, expected, test_case, expected_regexp=None):
        self.expected = expected
        self.failureException = test_case.failureException
        self.expected_regexp = expected_regexp

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            try:
                exc_name = self.expected.__name__
            except AttributeError:
                exc_name = str(self.expected)
            raise self.failureException(
                "{0} not raised".format(exc_name))
        if not issubclass(exc_type, self.expected):
            # let unexpected exceptions pass through
            return False
        self.exception = exc_value # store for later retrieval
        if self.expected_regexp is None:
            return True

        expected_regexp = self.expected_regexp
        if isinstance(expected_regexp, basestring):
            expected_regexp = re.compile(expected_regexp)
        if not expected_regexp.search(str(exc_value)):
            raise self.failureException('"%s" does not match "%s"' %
                     (expected_regexp.pattern, str(exc_value)))
        return True


class StacktachBaseTestCase(unittest.TestCase):

    def assertIsNotNone(self, obj, msg=None):
        self.assertTrue(obj is not None, msg)

    def assertIsNone(self, obj, msg=None):
        self.assertTrue(obj is None, msg)

    def assertIsInstance(self, obj, cls, msg=None):
        self.assertTrue(isinstance(obj, cls), msg)

    def assertIs(self, expr1, expr2, msg=None):
        self.assertTrue(expr1 is expr2, msg)

    def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
        context = _AssertRaisesContext(excClass, self)
        if callableObj is None:
            return context
        with context:
            callableObj(*args, **kwargs)
