# Copyright 2012 - Rackspace Inc.

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
