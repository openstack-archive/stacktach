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
import logging
import logging.handlers
import multiprocessing
import os
import re
import threading
import traceback
import sys
import time

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
    get_logger(name=name, is_parent=False).warn(msg)


def error(msg, name=None):
    if name is None:
        name = default_logger_name
    get_logger(name=name, is_parent=False).error(msg)


def info(msg, name=None):
    if name is None:
        name = default_logger_name
    get_logger(name=name, is_parent=False).info(msg)


def _create_timed_rotating_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = TimedRotatingFileHandlerWithCurrentTimestamp(
        default_logger_location % name, when='midnight', interval=1,
        backupCount=6)
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


class TimedRotatingFileHandlerWithCurrentTimestamp(
        logging.handlers.TimedRotatingFileHandler):

    def __init__(self, filename, when='h', interval=1, backupCount=0,
                 encoding=None, delay=False, utc=False):
        logging.handlers.TimedRotatingFileHandler.__init__(
            self, filename, when, interval, backupCount, encoding, delay, utc)
        self.suffix = "%Y-%m-%d_%H-%M-%S"
        self.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")

    def doRollover(self):
        """Exactly the same as TimedRotatingFileHandler's doRollover() except
        that the current date/time stamp is appended to the filename rather
        than the start date/time stamp, when the rollover happens."""
        currentTime = int(time.time())
        if self.stream:
            self.stream.close()
            self.stream = None
        if self.utc:
            timeTuple = time.gmtime(currentTime)
        else:
            timeTuple = time.localtime(currentTime)
        dfn = self.baseFilename + "." + time.strftime(self.suffix, timeTuple)
        if os.path.exists(dfn):
            os.remove(dfn)
        os.rename(self.baseFilename, dfn)
        if self.backupCount > 0:
            # find the oldest log file and delete it
            #s = glob.glob(self.baseFilename + ".20*")
            #if len(s) > self.backupCount:
            #    s.sort()
            #    os.remove(s[0])
            for s in self.getFilesToDelete():
                os.remove(s)
        #print "%s -> %s" % (self.baseFilename, dfn)
        self.mode = 'w'
        self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval
        #If DST changes and midnight or weekly rollover, adjust for this.
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dstNow = time.localtime(currentTime)[-1]
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            if dstNow != dstAtRollover:
                if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                    newRolloverAt = newRolloverAt - 3600
                else:           # DST bows out before next rollover, so we need to add an hour
                    newRolloverAt = newRolloverAt + 3600
        self.rolloverAt = newRolloverAt
