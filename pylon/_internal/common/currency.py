from enum import StrEnum
from typing import Any, Generic, Self, TypeVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema

RAO_PER_TAO = 1_000_000_000


class Token(StrEnum):
    TAO = "tao"
    ALPHA = "alpha"


TokenType = TypeVar("TokenType", bound=Token)


class Currency(Generic[TokenType], float):
    """
    Simple class representing Bittensor tokens.
    Supports conversion to and from RAO.
    """

    @classmethod
    def from_rao(cls, rao: "CurrencyRao[TokenType]") -> Self:
        return cls(rao / RAO_PER_TAO)

    def as_rao(self) -> "CurrencyRao[TokenType]":
        return CurrencyRao[TokenType](self * RAO_PER_TAO)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: type[Any], handler: GetCoreSchemaHandler) -> CoreSchema:
        return handler(float)


class CurrencyRao(Generic[TokenType], int):
    """
    Simple class representing Bittensor tokens expressed as RAO.
    To convert to a full token, use "from_rao" method on Currency class.
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: type[Any], handler: GetCoreSchemaHandler) -> CoreSchema:
        return handler(int)
