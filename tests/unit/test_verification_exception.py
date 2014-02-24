import datetime
import mox
from tests.unit import StacktachBaseTestCase
from verifier import NotFound, AmbiguousResults, FieldMismatch, NullFieldException, WrongTypeException


class VerificationExceptionTestCase(StacktachBaseTestCase):
    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_not_found_exception(self):
        exception = NotFound('object_type', 'search_params')

        self.assertEqual(exception.reason,
                         "Couldn't find object_type using search_params")

    def test_ambiguous_results_exception(self):
        exception = AmbiguousResults('object_type', 'search_params')

        self.assertEqual(
            exception.reason,
            "Ambiguous results for object_type using search_params")

    def test_field_mismatch_exception(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        exception = FieldMismatch('field_name', 'expected', 'actual', 'uuid')

        self.assertEqual(exception.reason,
                         "Failed at 2014-01-02 03:04:05 UTC for uuid: Expected"
                         " field_name to be 'expected' got 'actual'")

    def test_null_field_exception(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        exception = NullFieldException('field_name', '1234', 'uuid')

        self.assertEqual(exception.reason,
                         "Failed at 2014-01-02 03:04:05 UTC for uuid: "
                         "field_name field was null for exist id 1234")

    def test_wrong_type_exception(self):
        self.mox.StubOutWithMock(datetime, 'datetime')
        datetime.datetime.utcnow().AndReturn('2014-01-02 03:04:05')
        self.mox.ReplayAll()

        exception = WrongTypeException('field_name', 'value', '1234', 'uuid')

        self.assertEqual(exception.reason,
                         "Failed at 2014-01-02 03:04:05 UTC for uuid: "
                         "{field_name: value} was of incorrect type for"
                         " exist id 1234")

