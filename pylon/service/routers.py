from litestar import Router

from pylon._internal.common.apiver import ApiVersion
from pylon.service.api import (
    IdentityController,
    OpenAccessController,
)

v1_router = Router(
    path=ApiVersion.V1.prefix,
    route_handlers=[
        IdentityController,
        OpenAccessController,
    ],
)
