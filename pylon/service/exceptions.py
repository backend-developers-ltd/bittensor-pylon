from litestar import status_codes
from litestar.exceptions import InternalServerException


class BadGatewayException(InternalServerException):
    status_code = status_codes.HTTP_502_BAD_GATEWAY
