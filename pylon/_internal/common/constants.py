import re

# v1 endpoints
ENDPOINT_CERTIFICATES = "/api/v1/certificates"
ENDPOINT_CERTIFICATES_SELF = "/api/v1/certificates/self"
ENDPOINT_CERTIFICATES_HOTKEY = "/api/v1/certificates/{hotkey:str}"
ENDPOINT_SUBNET_WEIGHTS = "/api/v1/subnet/weights"


def format_endpoint(endpoint: str, **kwargs) -> str:
    # remove :int and :str from the endpoint to be able to format it
    return re.sub(r":(\w+)", "", endpoint).format(**kwargs)


def endpoint_name(endpoint: str) -> str:
    parts = endpoint.split("/")
    if len(parts) > 1:
        return parts[1]
    return endpoint
