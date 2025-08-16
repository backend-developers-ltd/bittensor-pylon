import functools
import logging

from litestar import Request, Response, get, post, put

from pylon_common.constants import (
    ENDPOINT_BLOCK_HASH,
    ENDPOINT_COMMITMENT,
    ENDPOINT_COMMITMENTS,
    ENDPOINT_EPOCH,
    ENDPOINT_EPOCH_BLOCK,
    ENDPOINT_FORCE_COMMIT_WEIGHTS,
    ENDPOINT_HYPERPARAMS,
    ENDPOINT_LATEST_BLOCK,
    ENDPOINT_LATEST_METAGRAPH,
    ENDPOINT_LATEST_WEIGHTS,
    ENDPOINT_METAGRAPH,
    ENDPOINT_SET_COMMITMENT,
    ENDPOINT_SET_HYPERPARAM,
    ENDPOINT_SET_WEIGHT,
    ENDPOINT_SET_WEIGHTS,
    ENDPOINT_UPDATE_WEIGHT,
    ENDPOINT_WEIGHTS_TYPED,
)
from pylon_common.models import (
    SetCommitmentRequest,
    SetHyperparamRequest,
    SetWeightRequest,
    SetWeightsRequest,
    UpdateWeightRequest,
)
from pylon_common.settings import settings
from pylon_service import db
from pylon_service.bittensor_client import (
    commit_weights,
    get_commitment,
    get_commitments,
    get_metagraph,
    get_weights,
    set_commitment,
    set_hyperparam,
)
from pylon_service.utils import get_epoch_containing_block

logger = logging.getLogger(__name__)


def validator_only(func):
    """Decorator to restrict endpoint access to validators only."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not settings.am_i_a_validator:
            logger.warning(f"Non-validator access attempt to {func.__name__}")
            return Response(
                status_code=403,
                content={"detail": "Endpoint available for validators only."},
            )
        return await func(*args, **kwargs)

    return wrapper


def subnet_owner_only(func):
    """Decorator to restrict endpoint access to subnet owners only."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # TODO: fix
        # if not subnet_owner:
        #     logger.warning(f"Non-subnet owner access attempt to {func.__name__}")
        #     return Response(
        #         status_code=403,
        #         content={"detail": "Endpoint available for subnet owners only."},
        #     )
        return await func(*args, **kwargs)

    return wrapper


def safe_endpoint(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            logger.info(f"{func.__name__}/ hit with: {kwargs.get('data', None)}")
            return await func(*args, **kwargs)
        except Exception as e:
            error_message = f"Error in endpoint {func.__name__}: {e}"
            logger.error(error_message)
            return Response(status_code=500, content={"detail": error_message})

    return wrapper


def get_latest_block(request: Request) -> int:
    """Helper to get the latest block number from app state."""
    block = request.app.state.latest_block
    if block is None:
        raise RuntimeError("Latest block not available. Try again later.")
    return block


def get_current_epoch(request: Request):
    """Helper to get the current epoch start block from app state."""
    epoch = request.app.state.current_epoch_start
    if epoch is None:
        raise RuntimeError("Current epoch not available. Try again later.")
    return epoch


@get("/health")
async def health_check(request: Request) -> Response:
    """
    Service is considered healthy when a latest block has been fetched.
    """
    if request.app.state.latest_block is None:
        return Response(status_code=503, content={"status": "loading"})
    return Response(status_code=200, content={"status": "ok"})


@get(ENDPOINT_LATEST_BLOCK)
@safe_endpoint
async def latest_block(request: Request) -> dict:
    """Get the latest processed block number."""
    block = get_latest_block(request)
    return {"block": block}


@get(ENDPOINT_LATEST_METAGRAPH)
@safe_endpoint
async def latest_metagraph(request: Request) -> dict:
    """Get the metagraph for the latest block from cache."""
    block = get_latest_block(request)
    metagraph = request.app.state.metagraph_cache.get(block)
    return metagraph.model_dump()


@get(ENDPOINT_METAGRAPH)
@safe_endpoint
async def metagraph(request: Request, block: int) -> dict:
    """Get the metagraph for a specific block number."""
    metagraph = await get_metagraph(request.app, block)
    return metagraph.model_dump()


# TODO: optimize call to not fetch metagraph - just the hash?
@get(ENDPOINT_BLOCK_HASH)
@safe_endpoint
async def block_hash(request: Request, block: int) -> dict:
    """Get the block hash for a specific block number."""
    metagraph = await get_metagraph(request.app, block)
    return {"block_hash": metagraph.block_hash}


@get(ENDPOINT_EPOCH)
@safe_endpoint
async def latest_epoch_start_endpoint(request: Request) -> dict:
    """Get information about the current epoch start."""
    epoch = get_current_epoch(request)
    return epoch.model_dump()


@get(ENDPOINT_EPOCH_BLOCK)
@safe_endpoint
async def epoch_start_endpoint(request: Request, block: int) -> dict:
    """Get epoch information for the epoch containing the given block number."""
    epoch = get_epoch_containing_block(block)
    return epoch.model_dump()


@get(ENDPOINT_HYPERPARAMS)
@safe_endpoint
async def get_hyperparams_endpoint(request: Request) -> Response:
    """Get cached subnet hyperparameters."""
    hyperparams = request.app.state.hyperparams
    if hyperparams is None:
        return Response({"detail": "Hyperparameters not cached yet."}, status_code=503)
    return Response(hyperparams, status_code=200)


@put(ENDPOINT_SET_HYPERPARAM)
@subnet_owner_only
@safe_endpoint
async def set_hyperparam_endpoint(request: Request, data: SetHyperparamRequest) -> Response:
    """
    Set a subnet hyperparameter.
    (Subnet owner only)
    """
    await set_hyperparam(request.app, data.name, data.value)
    return Response({"detail": "Hyperparameter set successfully"}, status_code=200)


@put(ENDPOINT_UPDATE_WEIGHT)
@validator_only
@safe_endpoint
async def update_weight_endpoint(request: Request, data: UpdateWeightRequest) -> Response:
    """
    Update a hotkey's weight by a delta for the current epoch.
    (Validator only)
    """
    epoch = get_current_epoch(request)
    weight = await db.update_weight(data.hotkey, data.weight_delta, epoch)
    return Response({"hotkey": data.hotkey, "weight": weight, "epoch": epoch}, status_code=200)


@put(ENDPOINT_SET_WEIGHT)
@validator_only
@safe_endpoint
async def set_weight_endpoint(request: Request, data: SetWeightRequest) -> Response:
    """
    Set a hotkey's weight for the current epoch.
    (Validator only)
    """
    epoch = get_current_epoch(request)
    await db.set_weight(data.hotkey, data.weight, epoch)
    return Response({"hotkey": data.hotkey, "weight": data.weight, "epoch": epoch}, status_code=200)


@put(ENDPOINT_SET_WEIGHTS)
@validator_only
@safe_endpoint
async def set_weights_endpoint(request: Request, data: SetWeightsRequest) -> Response:
    """
    Set multiple hotkeys' weights for the current epoch in a single transaction.
    (Validator only)
    """
    epoch = get_current_epoch(request)
    weights_list = [(hotkey, weight) for hotkey, weight in data.weights.items()]
    await db.set_weights_batch(weights_list, epoch)

    return Response({"weights": data.weights, "epoch": epoch, "count": len(data.weights)}, status_code=200)


# TODO: refactor to epochs_ago ?
@get(ENDPOINT_LATEST_WEIGHTS)
@safe_endpoint
async def latest_weights_endpoint(request: Request) -> Response:
    """
    Get raw weights for the current epoch.
    """
    epoch = get_current_epoch(request)
    weights = await db.get_hotkey_weights_dict(epoch)
    if weights == {}:
        return Response({"detail": "Epoch weights not found"}, status_code=404)
    return Response({"epoch": epoch, "weights": weights}, status_code=200)


@get(ENDPOINT_WEIGHTS_TYPED)
@safe_endpoint
async def weights_endpoint(request: Request, block: int) -> Response:
    """
    Get raw weights for the epoch containing the specified block.
    """
    epoch = get_epoch_containing_block(block).start
    weights = await db.get_hotkey_weights_dict(epoch)
    if weights == {}:
        return Response({"detail": "Epoch weights not found"}, status_code=404)
    return Response({"epoch": epoch, "weights": weights}, status_code=200)


@post(ENDPOINT_FORCE_COMMIT_WEIGHTS)
@validator_only
@safe_endpoint
async def force_commit_weights_endpoint(request: Request) -> Response:
    """
    Force commit of current DB weights to the subnet.
    (Validator only)
    """
    block = get_latest_block(request)
    weights = await get_weights(request.app, block)
    if not weights:
        msg = "Could not retrieve weights from db to commit"
        logger.warning(msg)
        return Response({"detail": msg}, status_code=404)

    await commit_weights(request.app, weights)

    return Response(
        {
            "block": block,
            "committed_weights": weights,
        },
        status_code=200,
    )


# TODO: wip, to update, to be register endpoints


@get(ENDPOINT_COMMITMENT)
@safe_endpoint
async def get_commitment_endpoint(request: Request, hotkey: str) -> Response:
    """
    Get a specific commitment (hex string) for a hotkey.
    Uses the configured netuid. Optional 'block' query param.
    """
    block = request.query_params.get("block", None)
    block = get_latest_block(request) if block is None else int(block)

    commitment = await get_commitment(request.app, hotkey, block)
    if commitment is None:
        return Response({"detail": "Commitment not found or error fetching."}, status_code=404)
    return Response({"hotkey": hotkey, "commitment": commitment}, status_code=200)


@get(ENDPOINT_COMMITMENTS)
@safe_endpoint
async def get_commitments_endpoint(request: Request) -> Response:
    """
    Get all commitments (hotkey: commitment_hex) for the configured subnet.
    Optional 'block' query param (for block_hash lookup).
    """
    block = request.query_params.get("block")
    block = get_latest_block(request) if block is None else int(block)
    commitments_map = await get_commitments(request.app, block)
    return Response(commitments_map, status_code=200)


@post(ENDPOINT_SET_COMMITMENT)
@safe_endpoint
async def set_commitment_endpoint(request: Request, data: SetCommitmentRequest) -> Response:
    """
    Set a commitment for the pylon_service's wallet on the configured subnet.
    """
    try:
        commitment_data = bytes.fromhex(data.data_hex)
    except ValueError:
        return Response({"detail": "Invalid 'data_hex' in request body"}, status_code=400)
    await set_commitment(request.app, commitment_data)
    return Response({"detail": "Commitment successfully set"}, status_code=200)
