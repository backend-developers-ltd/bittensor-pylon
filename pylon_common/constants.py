import re

# API endpoint paths
ENDPOINT_LATEST_BLOCK = "/latest_block"
ENDPOINT_LATEST_METAGRAPH = "/latest_metagraph"
ENDPOINT_METAGRAPH = "/metagraph/{block:int}"
ENDPOINT_BLOCK_HASH = "/block_hash/{block:int}"
ENDPOINT_EPOCH = "/epoch"
ENDPOINT_EPOCH_BLOCK = "/epoch/{block:int}"

ENDPOINT_HYPERPARAMS = "/hyperparams"
ENDPOINT_SET_HYPERPARAM = "/set_hyperparam"

ENDPOINT_UPDATE_WEIGHT = "/update_weight"
ENDPOINT_SET_WEIGHT = "/set_weight"
ENDPOINT_SET_WEIGHTS = "/set_weights"
ENDPOINT_LATEST_WEIGHTS = "/latest_weights"
ENDPOINT_WEIGHTS = "/weights/{block:int}"
ENDPOINT_WEIGHTS_TYPED = "/weights/{block:int}"
ENDPOINT_FORCE_COMMIT_WEIGHTS = "/force_commit_weights"

ENDPOINT_COMMITMENT = "/commitment/{hotkey:str}"
ENDPOINT_COMMITMENTS = "/commitments"
ENDPOINT_SET_COMMITMENT = "/set_commitment"


def format_endpoint(endpoint: str, **kwargs) -> str:
    # remove :int and :str from the endpoint to be able to format it
    return re.sub(r":(\w+)", "", endpoint).format(**kwargs)


def endpoint_name(endpoint: str) -> str:
    parts = endpoint.split("/")
    if len(parts) > 1:
        return parts[1]
    return endpoint
