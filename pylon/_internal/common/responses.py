from enum import StrEnum

from pydantic import BaseModel


class PylonResponseStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class PylonResponse(BaseModel):
    """
    Base class for Pylon response objects.

    Subclasses of this class are returned by the Pylon client, and they contain the relevant information
    returned by the Pylon API. Every Pylon request class has its respective response class that will be returned by
    the pylon client after performing a request.
    """

    status: PylonResponseStatus


class SetWeightsResponse(PylonResponse):
    """
    Response class that is returned for the SetWeightsRequest.
    """
    # TODO: Modify this model after set weights endpoint is made clean.

    pass
