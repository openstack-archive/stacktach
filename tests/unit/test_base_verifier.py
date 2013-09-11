import datetime
import time
from django.db import transaction
import mox
from stacktach import message_service
from tests.unit import StacktachBaseTestCase
from tests.unit.utils import HOST, PORT, VIRTUAL_HOST, USERID, PASSWORD, TICK_TIME, SETTLE_TIME, SETTLE_UNITS
from tests.unit.utils import make_verifier_config
from verifier import base_verifier


class BaseVerifierTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()
        config = make_verifier_config(False)
        self.pool = self.mox.CreateMockAnything()
        self.reconciler = self.mox.CreateMockAnything()
        self.verifier_with_reconciler = base_verifier.Verifier(config,
            pool=self.pool, reconciler=self.reconciler)
        self.verifier_without_notifications = self\
            ._verifier_with_notifications_disabled()
        self.verifier_with_notifications = self\
            ._verifier_with_notifications_enabled()

    def _verifier_with_notifications_disabled(self):
        config = make_verifier_config(False)
        reconciler = self.mox.CreateMockAnything()
        return base_verifier.Verifier(config,
                                      pool=self.pool,
                                      reconciler=reconciler)

    def _verifier_with_notifications_enabled(self):
        config = make_verifier_config(True)
        reconciler = self.mox.CreateMockAnything()
        return base_verifier.Verifier(config,
                                      pool=self.pool,
                                      reconciler=reconciler)

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_should_create_verifier_with_reconciler(self):
        config = make_verifier_config(False)
        rec = self.mox.CreateMockAnything()
        verifier = base_verifier.Verifier(config, pool=None, reconciler=rec)
        self.assertEqual(verifier.reconciler, rec)

    def test_clean_results_full(self):
        result_not_ready = self.mox.CreateMockAnything()
        result_not_ready.ready().AndReturn(False)
        result_unsuccessful = self.mox.CreateMockAnything()
        result_unsuccessful.ready().AndReturn(True)
        result_unsuccessful.successful().AndReturn(False)
        result_successful = self.mox.CreateMockAnything()
        result_successful.ready().AndReturn(True)
        result_successful.successful().AndReturn(True)
        result_successful.get().AndReturn((True, None))
        result_failed_verification = self.mox.CreateMockAnything()
        result_failed_verification.ready().AndReturn(True)
        result_failed_verification.successful().AndReturn(True)
        failed_exists = self.mox.CreateMockAnything()
        result_failed_verification.get().AndReturn((False, failed_exists))
        self.verifier_with_reconciler.results = [result_not_ready,
                                 result_unsuccessful,
                                 result_successful,
                                 result_failed_verification]
        self.mox.ReplayAll()
        (result_count, success_count, errored) = self.verifier_with_reconciler.clean_results()
        self.assertEqual(result_count, 1)
        self.assertEqual(success_count, 2)
        self.assertEqual(errored, 1)
        self.assertEqual(len(self.verifier_with_reconciler.results), 1)
        self.assertEqual(self.verifier_with_reconciler.results[0], result_not_ready)
        self.assertEqual(len(self.verifier_with_reconciler.failed), 1)
        self.assertEqual(self.verifier_with_reconciler.failed[0], result_failed_verification)
        self.mox.VerifyAll()

    def test_clean_results_pending(self):
        result_not_ready = self.mox.CreateMockAnything()
        result_not_ready.ready().AndReturn(False)
        self.verifier_with_reconciler.results = [result_not_ready]
        self.mox.ReplayAll()
        (result_count, success_count, errored) = self.verifier_with_reconciler.clean_results()
        self.assertEqual(result_count, 1)
        self.assertEqual(success_count, 0)
        self.assertEqual(errored, 0)
        self.assertEqual(len(self.verifier_with_reconciler.results), 1)
        self.assertEqual(self.verifier_with_reconciler.results[0], result_not_ready)
        self.assertEqual(len(self.verifier_with_reconciler.failed), 0)
        self.mox.VerifyAll()

    def test_clean_results_successful(self):
        self.verifier_with_reconciler.reconcile = True
        result_successful = self.mox.CreateMockAnything()
        result_successful.ready().AndReturn(True)
        result_successful.successful().AndReturn(True)
        result_successful.get().AndReturn((True, None))
        self.verifier_with_reconciler.results = [result_successful]
        self.mox.ReplayAll()
        (result_count, success_count, errored) = self.verifier_with_reconciler.clean_results()
        self.assertEqual(result_count, 0)
        self.assertEqual(success_count, 1)
        self.assertEqual(errored, 0)
        self.assertEqual(len(self.verifier_with_reconciler.results), 0)
        self.assertEqual(len(self.verifier_with_reconciler.failed), 0)
        self.mox.VerifyAll()

    def test_clean_results_unsuccessful(self):
        result_unsuccessful = self.mox.CreateMockAnything()
        result_unsuccessful.ready().AndReturn(True)
        result_unsuccessful.successful().AndReturn(False)
        self.verifier_with_reconciler.results = [result_unsuccessful]
        self.mox.ReplayAll()
        (result_count, success_count, errored) = \
            self.verifier_with_reconciler.clean_results()
        self.assertEqual(result_count, 0)
        self.assertEqual(success_count, 0)
        self.assertEqual(errored, 1)
        self.assertEqual(len(self.verifier_with_reconciler.results), 0)
        self.assertEqual(len(self.verifier_with_reconciler.failed), 0)
        self.mox.VerifyAll()

    def test_clean_results_fail_verification(self):
        result_failed_verification = self.mox.CreateMockAnything()
        result_failed_verification.ready().AndReturn(True)
        result_failed_verification.successful().AndReturn(True)
        failed_exists = self.mox.CreateMockAnything()
        result_failed_verification.get().AndReturn((False, failed_exists))
        self.verifier_with_reconciler.results = [result_failed_verification]
        self.mox.ReplayAll()
        (result_count, success_count, errored) = \
            self.verifier_with_reconciler.clean_results()
        self.assertEqual(result_count, 0)
        self.assertEqual(success_count, 1)
        self.assertEqual(errored, 0)
        self.assertEqual(len(self.verifier_with_reconciler.results), 0)
        self.assertEqual(len(self.verifier_with_reconciler.failed), 1)
        self.assertEqual(self.verifier_with_reconciler.failed[0], failed_exists)
        self.mox.VerifyAll()

    def test_run_notifications(self):
        self._mock_exchange_create_and_connect(self.verifier_with_notifications)
        self.mox.StubOutWithMock(self.verifier_with_notifications, '_run')
        self.verifier_with_notifications._run(callback=mox.Not(mox.Is(None)))
        self.mox.ReplayAll()
        self.verifier_with_notifications.run()
        self.mox.VerifyAll()

    def test_run_notifications_with_routing_keys(self):
        self._mock_exchange_create_and_connect(self.verifier_with_notifications)
        self.mox.StubOutWithMock(self.verifier_with_notifications, '_run')
        self.verifier_with_notifications._run(callback=mox.Not(mox.Is(None)))
        self.mox.ReplayAll()
        self.verifier_with_notifications.run()
        self.mox.VerifyAll()

    def test_run_no_notifications(self):
        self.mox.StubOutWithMock(self.verifier_without_notifications, '_run')
        self.verifier_without_notifications._run()
        self.mox.ReplayAll()
        self.verifier_without_notifications.run()
        self.mox.VerifyAll()

    def test_run_full_no_notifications(self):
        self.mox.StubOutWithMock(transaction, 'commit_on_success')
        tran = self.mox.CreateMockAnything()
        tran.__enter__().AndReturn(tran)
        tran.__exit__(mox.IgnoreArg(), mox.IgnoreArg(), mox.IgnoreArg())
        transaction.commit_on_success().AndReturn(tran)
        self.mox.StubOutWithMock(self.verifier_without_notifications, '_keep_running')
        self.verifier_without_notifications._keep_running().AndReturn(True)
        start = datetime.datetime.utcnow()
        self.mox.StubOutWithMock(self.verifier_without_notifications, '_utcnow')
        self.verifier_without_notifications._utcnow().AndReturn(start)
        settle_offset = {SETTLE_UNITS: SETTLE_TIME}
        ending_max = start - datetime.timedelta(**settle_offset)
        self.mox.StubOutWithMock(self.verifier_without_notifications, 'verify_for_range')
        self.verifier_without_notifications.verify_for_range(ending_max, callback=None)
        self.mox.StubOutWithMock(self.verifier_without_notifications, 'reconcile_failed')
        result1 = self.mox.CreateMockAnything()
        result2 = self.mox.CreateMockAnything()
        self.verifier_without_notifications.results = [result1, result2]
        result1.ready().AndReturn(True)
        result1.successful().AndReturn(True)
        result1.get().AndReturn((True, None))
        result2.ready().AndReturn(True)
        result2.successful().AndReturn(True)
        result2.get().AndReturn((True, None))
        self.verifier_without_notifications.reconcile_failed()
        self.mox.StubOutWithMock(time, 'sleep', use_mock_anything=True)
        time.sleep(TICK_TIME)
        self.verifier_without_notifications._keep_running().AndReturn(False)
        self.mox.ReplayAll()

        self.verifier_without_notifications.run()

        self.mox.VerifyAll()

    def test_run_full(self):
        self.mox.StubOutWithMock(transaction, 'commit_on_success')
        tran = self.mox.CreateMockAnything()
        tran.__enter__().AndReturn(tran)
        tran.__exit__(mox.IgnoreArg(), mox.IgnoreArg(), mox.IgnoreArg())
        transaction.commit_on_success().AndReturn(tran)
        self._mock_exchange_create_and_connect(self.verifier_with_notifications)
        self.verifier_with_notifications.exchange().AndReturn('exchange')
        self.mox.StubOutWithMock(self.verifier_with_notifications, '_keep_running')
        self.verifier_with_notifications._keep_running().AndReturn(True)
        start = datetime.datetime.utcnow()
        self.mox.StubOutWithMock(self.verifier_with_notifications, '_utcnow')
        self.verifier_with_notifications._utcnow().AndReturn(start)
        settle_offset = {SETTLE_UNITS: SETTLE_TIME}
        ending_max = start - datetime.timedelta(**settle_offset)
        self.mox.StubOutWithMock(self.verifier_with_notifications, 'verify_for_range')
        self.verifier_with_notifications.verify_for_range(ending_max,
                                             callback=mox.Not(mox.Is(None)))
        self.mox.StubOutWithMock(self.verifier_with_notifications, 'reconcile_failed')
        result1 = self.mox.CreateMockAnything()
        result2 = self.mox.CreateMockAnything()
        self.verifier_with_notifications.results = [result1, result2]
        result1.ready().AndReturn(True)
        result1.successful().AndReturn(True)
        result1.get().AndReturn((True, None))
        result2.ready().AndReturn(True)
        result2.successful().AndReturn(True)
        result2.get().AndReturn((True, None))
        self.verifier_with_notifications.reconcile_failed()
        self.mox.StubOutWithMock(time, 'sleep', use_mock_anything=True)
        time.sleep(TICK_TIME)
        self.verifier_with_notifications._keep_running().AndReturn(False)
        self.mox.ReplayAll()

        self.verifier_with_notifications.run()

        self.mox.VerifyAll()

    def _mock_exchange_create_and_connect(self, verifier):
        self.mox.StubOutWithMock(verifier, 'exchange')
        self.verifier_with_notifications.exchange().AndReturn('exchange')
        self.mox.StubOutWithMock(message_service, 'create_exchange')
        exchange = self.mox.CreateMockAnything()
        message_service.create_exchange('exchange', 'topic', durable=True) \
            .AndReturn(exchange)
        self.mox.StubOutWithMock(message_service, 'create_connection')
        conn = self.mox.CreateMockAnything()
        conn.__enter__().AndReturn(conn)
        conn.__exit__(None, None, None)
        message_service.create_connection(HOST, PORT, USERID,
                                          PASSWORD, "librabbitmq",
                                          VIRTUAL_HOST).AndReturn(conn)
