import typing

from pydantic import BaseModel, field_validator

from pylon._internal.common.apiver import ApiVersion
from pylon._internal.common.models import CertificateAlgorithm
from pylon._internal.common.responses import GetMetagraphResponse, PylonResponse, SetWeightsResponse
from pylon._internal.common.types import BlockNumber, Hotkey, Weight


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


class GetMetagraphRequest(PylonRequest):
    """
    Class used to fetch the metagraph by the Pylon client.
    """

    version = ApiVersion.V1
    response_cls = GetMetagraphResponse

    block_number: BlockNumber | None = None


class GenerateCertificateKeypairRequest(PylonRequest):
    algorithm: CertificateAlgorithm = CertificateAlgorithm.ED25519

    @field_validator("algorithm", mode="before")
    @classmethod
    def validate_algorithm(cls, v):
        if v != CertificateAlgorithm.ED25519:
            raise ValueError("Currently, only algorithm equals 1 is supported which is EdDSA using Ed25519 curve")
        return v
