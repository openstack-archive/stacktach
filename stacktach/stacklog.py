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
import multiprocessing
import threading
import traceback
import sys

LOGGERS = {}
LOGGER_QUEUE_MAP = {}
default_logger_location = '/var/log/stacktach/%s.log'
default_logger_name = 'stacktach-default'


def set_default_logger_location(loc):
    global default_logger_location
    default_logger_location = loc


def set_default_logger_name(name):
    global default_logger_name
    default_logger_name = name


class ParentLoggerDoesNotExist(Exception):
    def __init__(self, parent_logger_name):
        self.reason = "Cannot create child logger as parent logger with the" \
                      "name %s does not exist." % parent_logger_name


def _create_parent_logger(parent_logger_name):
    if parent_logger_name not in LOGGERS:
        logger = _create_timed_rotating_logger(parent_logger_name)
        LOGGERS[parent_logger_name] = logger
        LOGGER_QUEUE_MAP[parent_logger_name] = multiprocessing.Queue(-1)

    return LOGGERS[parent_logger_name]


def _create_child_logger(parent_logger_name):
    child_logger_name = "child_%s" % parent_logger_name
    if child_logger_name in LOGGERS:
        return LOGGERS[child_logger_name]
    if parent_logger_name in LOGGERS:
        queue = LOGGER_QUEUE_MAP[parent_logger_name]
        logger = _create_queue_logger(child_logger_name, queue)
        LOGGERS[child_logger_name] = logger
    else:
        raise ParentLoggerDoesNotExist(parent_logger_name)

    return LOGGERS[child_logger_name]


def _logger_factory(parent_logger_name, is_parent):
    if parent_logger_name is None:
        parent_logger_name = default_logger_name
    if is_parent:
        return _create_parent_logger(parent_logger_name)
    else:
        return _create_child_logger(parent_logger_name)


def get_logger(name=None, is_parent=True):
    return _logger_factory(name, is_parent)


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


def _create_timed_rotating_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.TimedRotatingFileHandler(
        default_logger_location % name,
        when='midnight', interval=1, backupCount=3)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.handlers[0].doRollover()
    return logger


def _create_queue_logger(name, queue):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = QueueHandler(queue)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


class QueueHandler(logging.Handler):
    def __init__(self, queue):
        logging.Handler.__init__(self)
        self.queue = queue

    def emit(self, record):
        try:
            # ensure that exc_info and args
            # have been stringified.  Removes any chance of
            # unpickleable things inside and possibly reduces
            # message size sent over the pipe
            if record.exc_info:
                # just to get traceback text into record.exc_text
                self.format(record)
                # remove exception info as it's not needed any more
                record.exc_info = None
            if record.args:
                record.msg = record.msg % record.args
                record.args = None
            self.queue.put_nowait(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class LogListener:
    def __init__(self, logger):
        self.logger = logger
        self.queue = get_queue(logger.name)

    def start(self):
        self.thread = threading.Thread(target=self._receive)
        self.thread.daemon = True
        self.thread.start()

    def _receive(self):
        while True:
            try:
                record = self.queue.get()
                # None is sent as a sentinel to tell the listener to quit
                if record is None:
                    break
                self.logger.handle(record)
            except (KeyboardInterrupt, SystemExit):
                raise
            except EOFError:
                break
            except:
                traceback.print_exc(file=sys.stderr)

    def end(self):
        self.queue.put_nowait(None)
        self.thread.join()
        for handler in self.logger.handlers:
            handler.close()


def get_queue(logger_name):
    return LOGGER_QUEUE_MAP[logger_name]
