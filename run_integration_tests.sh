#! /bin/bash

workingdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
django-admin.py test --pythonpath=$workingdir --settings=tests.integration.settings stacktach
