#!/bin/sh
virtualenv .venv
. .venv/bin/activate
pip install -r etc/pip-requires.txt
pip install -r etc/test-requires.txt
nosetests tests --exclude-dir=stacktach --with-coverage --cover-package=stacktach,worker,verifier --cover-erase

