#!/bin/bash
nosetests tests --exclude-dir=stacktach --with-coverage --cover-package=stacktach,worker
