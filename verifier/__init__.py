class VerificationException(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason


class NotFound(VerificationException):
    def __init__(self, object_type, search_params):
        self.object_type = object_type
        self.search_params = search_params
        self.reason = "Couldn't find %s using %s" % (self.object_type,
                                                     self.search_params)


class AmbiguousResults(VerificationException):
    def __init__(self, object_type, search_params):
        self.object_type = object_type
        self.search_params = search_params
        msg = "Ambiguous results for %s using %s" % (self.object_type,
                                                     self.search_params)
        self.reason = msg


class FieldMismatch(VerificationException):
    def __init__(self, field_name, expected, actual):
        self.field_name = field_name
        self.expected = expected
        self.actual = actual
        self.reason = "Expected %s to be '%s' got '%s'" % (self.field_name,
                                                           self.expected,
                                                           self.actual)
