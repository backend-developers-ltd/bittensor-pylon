from httpx import Request, Response


class BasePylonException(Exception):
    """
    Base class for every pylon exception.
    """


class PylonRequestException(BasePylonException):
    """
    Error that pylon client issues on a failed request (after all retries failed).
    """

    def __init__(self, msg: str, request: Request):
        super().__init__(msg)
        self.msg = msg
        self.request = request


class PylonHttpStatusException(BasePylonException):
    """
    Error that pylon client issues on a non 2XX HTTP status response.
    """

    def __init__(self, msg: str, status: int, request: Request, response: Response):
        super().__init__(msg)
        self.msg = msg
        self.status = status
        self.request = request
        self.response = response
