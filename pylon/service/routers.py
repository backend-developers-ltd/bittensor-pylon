from litestar import Router

from pylon._internal.common.apiver import ApiVersion
from pylon.service.api import (
    generate_certificate_keypair_endpoint,
    get_certificate_endpoint,
    get_certificates_endpoint,
    get_metagraph,
    get_own_certificate_endpoint,
    put_weights_endpoint,
)

v1_router = Router(
    path=ApiVersion.V1.prefix,
    route_handlers=[
        get_metagraph,
        put_weights_endpoint,
        get_certificate_endpoint,
        get_certificates_endpoint,
        get_own_certificate_endpoint,
        generate_certificate_keypair_endpoint,
    ],
)
