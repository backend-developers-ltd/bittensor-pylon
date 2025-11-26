from pydantic import BaseModel

from pylon._internal.common.models import SubnetNeurons
from pylon._internal.common.types import CommitmentData, Hotkey


class PylonResponse(BaseModel):
    """
    Base class for Pylon response objects.

    Subclasses of this class are returned by the Pylon client, and they contain the relevant information
    returned by the Pylon API.
    Every Pylon request class has its respective response class that will be returned by
    the pylon client after performing a request.
    """


class SetWeightsResponse(PylonResponse):
    """
    Response class that is returned for the SetWeightsRequest.
    """

    # TODO: Modify this model after set weights endpoint is made clean.

    pass


class GetNeuronsResponse(PylonResponse, SubnetNeurons):
    """
    Response class that is returned for the GetNeuronsRequest.
    """

    pass


class SetCommitmentResponse(PylonResponse):
    """
    Response class that is returned for the SetCommitmentRequest.
    """

    pass


class GetCommitmentResponse(PylonResponse):
    """
    Response class that is returned for the GetCommitmentRequest.
    """

    hotkey: Hotkey
    data: CommitmentData | None


class GetCommitmentsResponse(PylonResponse):
    """
    Response class that is returned for the GetCommitmentsRequest.
    """

    commitments: dict[Hotkey, CommitmentData]
