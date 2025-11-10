"""Litestar OpenAPI schema plugin for custom types."""

from typing import get_origin

from litestar._openapi.schema_generation import SchemaCreator
from litestar.openapi.spec import OpenAPIType, Schema
from litestar.plugins import OpenAPISchemaPlugin
from litestar.typing import FieldDefinition

from pylon._internal.common.currency import Currency, CurrencyRao


class PylonSchemaPlugin(OpenAPISchemaPlugin):
    """
    Plugin to generate OpenAPI schema for custom classes used in Pylon.

    To add support for a new class, add it to CUSTOM_TYPE_SCHEMA_MAP.
    """

    CUSTOM_TYPE_SCHEMA_MAP: dict[type, Schema] = {
        Currency: Schema(type=OpenAPIType.NUMBER),
        CurrencyRao: Schema(type=OpenAPIType.INTEGER),
    }
    SUPPORTED_TYPES = tuple(CUSTOM_TYPE_SCHEMA_MAP.keys())

    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        annotation_type = get_origin(field_definition.annotation)
        # Check direct type - we want to be precise here so no issubclass
        return annotation_type in self.SUPPORTED_TYPES

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        annotation_type = get_origin(field_definition.annotation)
        return self.CUSTOM_TYPE_SCHEMA_MAP[annotation_type]
