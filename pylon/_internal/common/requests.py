import typing

from pydantic import BaseModel, field_validator

from pylon._internal.common.apiver import ApiVersion
from pylon._internal.common.models import CertificateAlgorithm
from pylon._internal.common.responses import (
    GetCommitmentResponse,
    GetCommitmentsResponse,
    GetNeuronsResponse,
    PylonResponse,
    SetCommitmentResponse,
    SetWeightsResponse,
)
from pylon._internal.common.types import BlockNumber, CommitmentData, Hotkey, Weight


class PylonRequest(BaseModel):
    """
    Base class for all Pylon requests.

    Pylon requests are objects supplied to the Pylon client to make a request. Each class represents an action
    (e.g., setting weights) and defines arguments needed to perform the action.
    Every Pylon request class has its respective response class that will be returned by
    the pylon client after performing a request.
    """

    rtype: typing.ClassVar[str]
    version: typing.ClassVar[ApiVersion]
    response_cls: typing.ClassVar[type[PylonResponse]]


class SetWeightsRequest(PylonRequest):
    """
    Class used to perform setting weights by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = SetWeightsResponse

    weights: dict[Hotkey, Weight]

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v):
        if not v:
            raise ValueError("No weights provided")

        for hotkey, weight in v.items():
            if not hotkey or not isinstance(hotkey, str):
                raise ValueError(f"Invalid hotkey: '{hotkey}' must be a non-empty string")
            if not isinstance(weight, int | float):
                raise ValueError(f"Invalid weight for hotkey '{hotkey}': '{weight}' must be a number")

        return v


class GetNeuronsRequest(PylonRequest):
    """
    Class used to fetch the neurons by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetNeuronsResponse

    block_number: BlockNumber


class GetLatestNeuronsRequest(PylonRequest):
    """
    Class used to fetch the latest neurons by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetNeuronsResponse


class GenerateCertificateKeypairRequest(PylonRequest):
    algorithm: CertificateAlgorithm = CertificateAlgorithm.ED25519

    @field_validator("algorithm", mode="before")
    @classmethod
    def validate_algorithm(cls, v):
        if v != CertificateAlgorithm.ED25519:
            raise ValueError("Currently, only algorithm equals 1 is supported which is EdDSA using Ed25519 curve")
        return v


class SetCommitmentRequest(PylonRequest):
    """
    Class used to set a commitment (model metadata) on chain by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = SetCommitmentResponse

    data: CommitmentData

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, v):
        if isinstance(v, str):
            # Allow hex string input, convert to bytes
            if v.startswith("0x"):
                v = v[2:]
            return bytes.fromhex(v)
        if not isinstance(v, bytes):
            raise ValueError("data must be bytes or hex string")
        return v


class GetCommitmentRequest(PylonRequest):
    """
    Class used to fetch a commitment for a specific hotkey by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetCommitmentResponse

    hotkey: Hotkey


class GetCommitmentsRequest(PylonRequest):
    """
    Class used to fetch all commitments for the subnet by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetCommitmentsResponse
