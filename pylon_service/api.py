import functools
import logging

from litestar import Request, Response, get, post, put

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
from pylon_service.settings import settings
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
            logger.debug(f"Endpoint '{func.__name__}' hit.")
            return await func(*args, **kwargs)
        except Exception as e:
            error_message = f"Error in endpoint {func.__name__}: {e}"
            logger.error(error_message, exc_info=True)
            return Response(status_code=500, content={"detail": error_message})

    return wrapper


def get_latest_block(request: Request) -> int:
    """Helper to get the latest block number from app state."""
    block_number = request.app.state.latest_block
    if block_number is None:
        raise RuntimeError("Latest block not available. Try again later.")
    return block_number


def get_current_epoch(request: Request):
    """Helper to get the current epoch start block from app state."""
    epoch = request.app.state.current_epoch_start
    if epoch is None:
        raise RuntimeError("Current epoch not available. Try again later.")
    return epoch


@get("/health")
async def health_check() -> Response:
    """A simple health check endpoint."""
    return Response(status_code=200, content={"status": "ok"})


@get("/latest_block")
@safe_endpoint
async def latest_block(request: Request) -> dict:
    """Get the latest processed block number."""
    block = get_latest_block(request)
    return {"block": block}


@get("/metagraph")
@safe_endpoint
async def latest_metagraph(request: Request) -> dict:
    """Get the metagraph for the latest block from cache."""
    block = get_latest_block(request)
    metagraph = request.app.state.metagraph_cache.get(block)
    return metagraph.model_dump()


@get("/metagraph/{block_number:int}")
@safe_endpoint
async def metagraph(request: Request, block_number: int) -> dict:
    """Get the metagraph for a specific block number."""
    metagraph = await get_metagraph(request.app, block_number)
    return metagraph.model_dump()


# TODO: optimize call to not fetch metagraph - just the hash?
@get("/block_hash/{block_number:int}")
@safe_endpoint
async def block_hash(request: Request, block_number: int) -> dict:
    """Get the block hash for a specific block number."""
    metagraph = await get_metagraph(request.app, block_number)
    return {"block_hash": metagraph.block_hash}


@get("/epoch")
@safe_endpoint
async def latest_epoch_start(request: Request) -> dict:
    """Get information about the current epoch start."""
    epoch = get_current_epoch(request)
    return epoch.model_dump()


@get("/epoch/{block_number:int}")
@safe_endpoint
async def epoch_start(request: Request, block_number: int) -> dict:
    """Get epoch information for the epoch containing the given block number."""
    epoch = get_epoch_containing_block(block_number)
    return epoch.model_dump()


@get("/hyperparams")
@safe_endpoint
async def get_hyperparams_endpoint(request: Request) -> Response:
    """Get cached subnet hyperparameters."""
    hyperparams = request.app.state.hyperparams
    if hyperparams is None:
        return Response({"detail": "Hyperparameters not cached yet."}, status_code=503)
    return Response(hyperparams, status_code=200)


@put("/set_hyperparam")
@subnet_owner_only
@safe_endpoint
async def set_hyperparam_endpoint(request: Request) -> Response:
    """
    Set a subnet hyperparameter.
    Body: {"name": "<hyperparameter_name>", "value": <hyperparameter_value>}
    (Subnet owner only)
    """
    data = await request.json()
    name = data.get("name")
    value = data.get("value")
    if name is None:
        return Response({"detail": "Missing hyperparameter name"}, status_code=400)
    if value is None:
        return Response({"detail": "Missing hyperparameter value"}, status_code=400)
    await set_hyperparam(request.app, name, value)
    return Response({"detail": "Hyperparameter set successfully"}, status_code=200)


@put("/update_weight")
@validator_only
@safe_endpoint
async def update_weight(request: Request) -> Response:
    """
    Update a hotkey's weight by a delta for the current epoch.
    Body: {"hotkey": "<ss58_hotkey>", "weight_delta": <float>}
    (Validator only)
    """
    data = await request.json()
    hotkey = data.get("hotkey")
    delta = data.get("weight_delta")
    if hotkey is None:
        return Response({"detail": "Missing hotkey"}, status_code=400)
    if delta is None:
        return Response({"detail": "Missing weight_delta"}, status_code=400)

    epoch = get_current_epoch(request)
    weight = await db.update_weight(hotkey, delta, epoch)
    return Response({"hotkey": hotkey, "weight": weight, "epoch": epoch}, status_code=200)


@put("/set_weight")
@validator_only
@safe_endpoint
async def set_weight(request: Request) -> Response:
    """
    Set a hotkey's weight for the current epoch.
    Body: {"hotkey": "<ss58_hotkey>", "weight": <float>}
    (Validator only)
    """
    data = await request.json()
    hotkey = data.get("hotkey")
    weight = data.get("weight")
    if hotkey is None:
        return Response({"detail": "Missing hotkey"}, status_code=400)
    if weight is None:
        return Response({"detail": "Missing weight"}, status_code=400)

    epoch = get_current_epoch(request)
    await db.set_weight(hotkey, weight, epoch)
    return Response({"hotkey": hotkey, "weight": weight, "epoch": epoch}, status_code=200)


# TODO: refactor to epochs_ago ?
@get("/raw_weights")
@safe_endpoint
async def raw_weights(request: Request) -> Response:
    """
    Get raw weights for a given epoch (defaults to current epoch).
    Query param: 'epoch' (int, epoch start block)
    """
    epoch = request.query_params.get("epoch", None)
    epoch = int(epoch) if epoch is not None else get_current_epoch(request)
    epoch = get_epoch_containing_block(epoch).epoch_start  # in case epoch start block is incorrect
    weights = await db.get_raw_weights(epoch)
    if weights == {}:
        return Response({"detail": "Epoch weights not found"}, status_code=404)
    return Response({"epoch": epoch, "weights": weights}, status_code=200)


@post("/force_commit_weights")
@validator_only
@safe_endpoint
async def force_commit_weights(request: Request) -> Response:
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


@get("/get_commitment/{hotkey:str}")
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


@get("/get_commitments")
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


@post("/set_commitment")
@safe_endpoint
async def set_commitment_endpoint(request: Request) -> Response:
    """
    Set a commitment for the pylon_service's wallet on the configured subnet.
    Body: {"data_hex": "<commitment_hex_string>"}
    """
    data = await request.json()
    data_hex = data.get("data_hex")
    if not data_hex:
        return Response({"detail": "Missing 'data_hex' in request body"}, status_code=400)
    try:
        data = bytes.fromhex(data_hex)
    except ValueError:
        return Response({"detail": "Invalid 'data_hex' in request body"}, status_code=400)
    await set_commitment(request.app, data)
    return Response({"detail": "Commitment successfully set"}, status_code=200)
