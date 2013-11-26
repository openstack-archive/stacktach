import logging
import mox
from stacktach import stacklog
from tests.unit import StacktachBaseTestCase


class StacklogTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_get_logger_should_create_timed_rotating_logger_for_parent(self):
        logger_name = 'logger'
        logger = stacklog.get_logger(logger_name, is_parent=True)
        self.assertIsInstance(
            logger.handlers[0], logging.handlers.TimedRotatingFileHandler)
        self.assertEquals(logger.handlers[0].when, 'MIDNIGHT')
        self.assertEquals(logger.handlers[0].interval, 86400)
        self.assertEquals(logger.handlers[0].backupCount, 6)
        self.assertEqual(logger.name, 'logger')
        self.assertEquals(logger.level, logging.DEBUG)

    def test_get_logger_should_create_queue_logger_for_child(self):
        logger_name = 'logger'
        stacklog.get_logger(logger_name, is_parent=True)
        child_logger = stacklog.get_logger(logger_name, is_parent=False)
        self.assertIsInstance(
            child_logger.handlers[0], stacklog.QueueHandler)
        self.assertEqual(child_logger.name, 'child_logger')
        self.assertEquals(child_logger.level, logging.DEBUG)

    def test_get_logger_should_use_default_name_when_name_not_specified(self):
        logger = stacklog.get_logger(None, is_parent=True)
        self.assertEquals(logger.name, stacklog.default_logger_name)

        stacklog.set_default_logger_name('default')
        logger = stacklog.get_logger(None, is_parent=True)
        self.assertEquals(logger.name, 'default')

    def test_get_logger_raise_exception_when_child_created_before_parent(self):
        with self.assertRaises(stacklog.ParentLoggerDoesNotExist):
            stacklog.get_logger('logger', is_parent=False)

    def test_get_logger_should_return_existing_parent_logger_if_present(self):
        logger_1 = stacklog.get_logger('logger', is_parent=True)
        logger_2 = stacklog.get_logger('logger', is_parent=True)

        self.assertIs(logger_1, logger_2)

    def test_get_logger_should_return_existing_child_logger_if_present(self):
        stacklog.get_logger('logger', is_parent=True)
        child_logger_1 = stacklog.get_logger('logger', is_parent=False)
        child_logger_2 = stacklog.get_logger('logger', is_parent=False)

        self.assertIs(child_logger_1, child_logger_2)
