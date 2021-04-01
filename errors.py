"""Iris errors/exceptions"""


class IrisError(Exception):
    """Base class for other Iris exceptions"""

    pass


class TestCaseNotFound(IrisError):
    """Raised when test case is not found"""

    pass
