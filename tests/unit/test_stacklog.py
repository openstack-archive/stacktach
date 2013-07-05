import glob
import logging
import os
from unittest import TestCase
import mox
from stacktach import stacklog
import __builtin__
from stacktach.stacklog import ExchangeLogger


class StacklogTestCase(TestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_get_logger_should_get_exchange_logger_if_exchange_provided(self):
        filename = 'filename'
        logger = stacklog.get_logger(filename, 'nova')
        self.assertIsInstance(logger, ExchangeLogger)
        for file in glob.glob('{0}.log*'.format(filename)):
            os.remove(file)

    def test_get_logger_should_get_default_logger_if_exchange_not_provided(self):
        filename = 'default_logger'
        logger = stacklog.get_logger(filename)
        self.assertIsInstance(logger, logging.Logger)
        for file in glob.glob('{0}.log*'.format(filename)):
            os.remove(file)


class ExchangeLoggerTestCase(TestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def _setup_logger_mocks(self, name='name'):
        mock_logger = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(logging, 'getLogger')
        logging.getLogger(name).AndReturn(mock_logger)
        mock_logger.setLevel(logging.DEBUG)
        self.mox.StubOutClassWithMocks(logging.handlers,
                                       'TimedRotatingFileHandler')
        filename = "{0}.log".format(name)
        handler = logging.handlers.TimedRotatingFileHandler(
            filename, backupCount=3, interval=1, when='midnight')
        self.mox.StubOutClassWithMocks(logging, 'Formatter')
        mock_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(mock_formatter)
        mock_logger.addHandler(handler)
        mock_logger.handlers = [handler]
        handler.doRollover()
        return mock_logger

    def test_exchange_logger_should_append_exchange_name_to_info(self):
        mock_logger = self._setup_logger_mocks()
        mock_logger.info('exchange: Log %s', 'args', xyz='xyz')
        self.mox.ReplayAll()

        log = ExchangeLogger('exchange', 'name')
        log.info("Log %s", 'args', xyz='xyz')
        self.mox.VerifyAll()

    def test_exchange_logger_should_append_exchange_name_to_warn(self):
        mock_logger = self._setup_logger_mocks()
        mock_logger.warn('exchange: Log %s', 'args', xyz='xyz')
        self.mox.ReplayAll()

        logger = ExchangeLogger('exchange', 'name')
        logger.warn("Log %s", 'args', xyz='xyz')
        self.mox.VerifyAll()

    def test_exchange_logger_should_append_exchange_name_to_error(self):
        mock_logger = self._setup_logger_mocks()
        mock_logger.error('exchange: Log %s', 'args', xyz='xyz')
        self.mox.ReplayAll()

        logger = ExchangeLogger('exchange', 'name')
        logger.error("Log %s", 'args', xyz='xyz')
        self.mox.VerifyAll()

    def test_exchange_logger_should_append_exchange_name_to_exception(self):
        mock_logger = self._setup_logger_mocks()
        mock_logger.error('exchange: Log %s', 'args', xyz='xyz')
        self.mox.ReplayAll()

        logger = ExchangeLogger('exchange', 'name')
        logger.exception("Log %s", 'args', xyz='xyz')
        self.mox.VerifyAll()

    def test_exchange_logger_should_use_default_name_if_not_provided(self):
        self._setup_logger_mocks('stacktach-default')
        self.mox.ReplayAll()

        ExchangeLogger('exchange')
        self.mox.VerifyAll()


