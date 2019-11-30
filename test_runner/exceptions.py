class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class InputError(Error):
    # TODO: modify this to define on which step error happened etc.
    # And give proper name
    """Exception raised for errors in the input.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message
