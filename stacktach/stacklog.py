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
import logging.handlers

LOGGERS = {}
default_logger_location = '/var/log/stacktach/%s.log'
default_logger_name = 'stacktach-default'


def set_default_logger_location(loc):
    global default_logger_location
    default_logger_location = loc


def set_default_logger_name(name):
    global default_logger_name
    default_logger_name = name


def _logger_factory(exchange, name):
    if exchange:
        return ExchangeLogger(exchange, name)
    else:
        logger = logging.getLogger(__name__)
        _configure(logger, name)
        return logger


def _make_logger(name, exchange=None):
    log = _logger_factory(exchange, name)
    return log


def init_logger(name=None, exchange=None):
    global LOGGERS
    if name is None:
        name = default_logger_name
    if name not in LOGGERS:
        LOGGERS[name] = _make_logger(name, exchange)


def get_logger(name=None, exchange=None):
    global LOGGERS
    if name is None:
        name = default_logger_name
    init_logger(name=name, exchange=exchange)
    return LOGGERS[name]


def warn(msg, name=None):
    if name is None:
        name = default_logger_name
    get_logger(name=name).warn(msg)


def error(msg, name=None):
    if name is None:
        name = default_logger_name
    get_logger(name=name).error(msg)


def info(msg, name=None):
    if name is None:
        name = default_logger_name
    get_logger(name=name).info(msg)


def _configure(logger, name):
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.TimedRotatingFileHandler(
            default_logger_location % name,
            when='midnight', interval=1, backupCount=3)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.handlers[0].doRollover()


class ExchangeLogger():
    def __init__(self, exchange, name='stacktach-default'):
        self.logger = logging.getLogger(__name__)
        _configure(self.logger, name)
        self.exchange = exchange

    def info(self, msg, *args, **kwargs):
        msg = self.exchange + ': ' + msg
        self.logger.info(msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        msg = self.exchange + ': ' + msg
        self.logger.warn(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        msg = self.exchange + ': ' + msg
        self.logger.error(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        msg = self.exchange + ': ' + msg
        self.logger.error(msg, *args, **kwargs)