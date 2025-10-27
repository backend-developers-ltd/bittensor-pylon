class BasePylonException(Exception):
    """
    Base class for every pylon exception.
    """


class PylonRequestException(BasePylonException):
    """
    Error that pylon client issues when it fails to deliver the request to Pylon.
    """


class PylonResponseException(BasePylonException):
    """
    Error that pylon client issues on receiving an error response from Pylon.
    """
