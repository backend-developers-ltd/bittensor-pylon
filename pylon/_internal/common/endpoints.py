import re
from enum import StrEnum

from pylon._internal.common.apiver import ApiVersion


class Endpoint(StrEnum):
    CERTIFICATES = "/certificates"
    CERTIFICATES_SELF = "/certificates/self"
    CERTIFICATES_HOTKEY = "/certificates/{hotkey:str}"
    SUBNET_WEIGHTS = "/subnet/weights"

    def for_version(self, version: ApiVersion):
        return f"{version.prefix}{self}"
