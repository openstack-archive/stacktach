# Copyright (c) 2013 - Rackspace Inc.
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

import logging

LOGGERS = {}
default_logger_name = 'stacktach-default'


def set_default_logger_name(name):
    global default_logger_name
    default_logger_name = name


def _make_logger(name):
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    handler = logging.handlers.TimedRotatingFileHandler('%s.log' % name,
                                            when='midnight', interval=1, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.handlers[0].doRollover()
    return log


def init_logger(name=None):
    global LOGGERS
    if name is None:
        name = default_logger_name
    if name not in LOGGERS:
        LOGGERS[name] = _make_logger(name)


def get_logger(name=None):
    global LOGGERS
    if name is None:
        name = default_logger_name
    init_logger(name=name)
    return LOGGERS[name]


def warn(msg, name=None):
    if name is None:
        name = default_logger_name
    get_logger(name=name).warn(msg)


def error(msg, name=None):
    if name is None:
        name = default_logger_name
    get_logger(name=name).warn(msg)