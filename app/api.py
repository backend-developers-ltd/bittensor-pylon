import functools
import logging

from litestar import Request, Response, get, post, put

from app import db
from app.bittensor_client import (
    commit_weights,
    get_metagraph,
    get_weights,
)
from app.settings import settings
from app.utils import get_epoch_containing_block

logger = logging.getLogger(__name__)


def validator_only(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not settings.am_i_a_validator:
            logger.warning(f"Not running as validator: can't access {func.__name__}")
            return Response(
                status_code=403,
                content={"detail": "This endpoint is available only for validators."},
            )
        return await func(*args, **kwargs)

    return wrapper


def safe_endpoint(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_message = f"Error in endpoint {func.__name__}: {e}"
            logger.error(error_message, exc_info=True)
            return Response(status_code=500, content=error_message)

    return wrapper


def get_latest_block(request: Request):
    block_number = request.app.state.latest_block
    if block_number is None:
        raise RuntimeError("Latest block not available - try again later")
    return block_number


def get_current_epoch(request: Request):
    epoch = request.app.state.current_epoch_start
    if epoch is None:
        raise RuntimeError("Latest epoch not available - try again later")
    return epoch


@get("/latest_block")
@safe_endpoint
async def latest_block(request: Request) -> dict:
    block = get_latest_block(request)
    return {"block": block}


@get("/metagraph")
@safe_endpoint
async def latest_metagraph(request: Request) -> dict:
    block = get_latest_block(request)
    metagraph = request.app.state.metagraph_cache.get(block)
    return metagraph.model_dump()


@get("/metagraph/{block_number:int}")
@safe_endpoint
async def metagraph(request: Request, block_number: int) -> dict:
    metagraph = await get_metagraph(request.app, block_number)
    return metagraph.model_dump()


# TODO: optimize call to not fetch metagraph - just the hash?
@get("/block_hash/{block_number:int}")
@safe_endpoint
async def block_hash(request: Request, block_number: int) -> dict:
    metagraph = await get_metagraph(request.app, block_number)
    return {"block_hash": metagraph.block_hash}


@get("/epoch")
@safe_endpoint
async def latest_epoch_start(request: Request) -> dict:
    epoch = get_current_epoch(request)
    return epoch.model_dump()


@get("/epoch/{block_number:int}")
@safe_endpoint
async def epoch_start(request: Request, block_number: int) -> dict:
    epoch = get_epoch_containing_block(block_number)
    return epoch.model_dump()


@get("/hyperparams")
@safe_endpoint
async def hyperparams(request: Request) -> dict:
    """
    Returns subnet hyperparameters from memory (cache). No network call.
    """
    hyperparams = request.app.state.hyperparams
    if hyperparams is None:
        return {"detail": "Hyperparameters not available in cache yet.", "status_code": 503}
    return hyperparams


@put("/update_weight")
@validator_only
@safe_endpoint
async def update_weight(request: Request) -> dict:
    """
    Update a hotkey's weight by adding the given number to the current running total for that hotkey.
    params: weight_delta (float/int), hotkey (str)
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
    return {"hotkey": hotkey, "weight": weight, "epoch": epoch}


@put("/set_weight")
@validator_only
@safe_endpoint
async def set_weight(request: Request) -> dict:
    """
    Set a hotkey's weight, replacing whatever is there already.
    params: weight (float/int), hotkey (str)
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
    return {"hotkey": hotkey, "weight": weight, "epoch": epoch}


# TODO: refactor to epochs_ago ?
@get("/raw_weights")
@safe_endpoint
async def raw_weights(request: Request) -> dict:
    """
    Get raw weights for given epoch.
    params: epoch (int)
    """
    epoch = request.query_params.get("epoch", None)
    epoch = int(epoch) if epoch is not None else get_current_epoch(request)
    epoch = get_epoch_containing_block(epoch).epoch_start  # in case epoch start block is incorrect
    weights = await db.get_raw_weights(epoch)
    if weights == {}:
        return Response({"detail": "Epoch weights not found"}, status_code=404)
    return {"epoch": epoch, "weights": weights}


@post("/force_commit_weights")
@validator_only
@safe_endpoint
async def force_commit_weights(request: Request) -> dict:
    """
    Commit the latest weights from the db to the subnet now.
    """
    block = get_latest_block(request)
    weights = await get_weights(request.app, block)
    if not weights:
        msg = "Could not retrieve weights from db to commit"
        logger.warning(msg)
        return Response({"detail": msg}, status_code=404)

    await commit_weights(request.app, weights)

    return {
        "block": block,
        "committed_weights": weights,
    }
