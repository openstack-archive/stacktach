import mox
from tests.unit import StacktachBaseTestCase, utils
from verifier import NotFound, AmbiguousResults, FieldMismatch
from verifier import NullFieldException, WrongTypeException


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
        utils.mock_datetime_utcnow(self.mox, '2014-01-02 03:04:05')

        exception = FieldMismatch(
            'field_name',
            {'name': 'entity1', 'value': 'expected'},
            {'name': 'entity2', 'value': 'actual'},
            'uuid')

        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for uuid: Data mismatch for "
            "'field_name' - 'entity1' contains 'expected' but 'entity2' "
            "contains 'actual'")

    def test_null_field_exception(self):
        utils.mock_datetime_utcnow(self.mox, '2014-01-02 03:04:05')

        exception = NullFieldException('field_name', 'exist_id', 'uuid')

        self.assertEqual(exception.field_name, 'field_name')
        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for uuid: field_name field was "
            "null for exist id exist_id")

    def test_wrong_type_exception(self):
        utils.mock_datetime_utcnow(self.mox, '2014-01-02 03:04:05')

        exception = WrongTypeException(
            'field_name', 'value', 'exist_id', 'uuid')
        self.assertEqual(exception.field_name, 'field_name')
        self.assertEqual(exception.value, 'value')
        self.assertEqual(exception.exist_id, 'exist_id')
        self.assertEqual(exception.uuid, 'uuid')
        self.assertEqual(
            exception.reason,
            "Failed at 2014-01-02 03:04:05 UTC for uuid: {field_name: value} "
            "was of incorrect type for exist id exist_id")
