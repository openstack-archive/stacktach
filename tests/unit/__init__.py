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

import os
import sys

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
