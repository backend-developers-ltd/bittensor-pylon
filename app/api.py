import functools
import logging

from litestar import Request, Response, get

from app.bittensor_client import get_metagraph
from app.utils import get_epoch_containing_block

logger = logging.getLogger(__name__)


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


@get("/block_hash/{block_number:int}")
@safe_endpoint
async def block_hash(request: Request, block_number: int) -> dict:
    metagraph = await get_metagraph(request.app, block_number)
    return {"block_hash": metagraph.block_hash}


@get("/epoch")
@safe_endpoint
async def latest_epoch_start(request: Request) -> dict:
    block_number = get_latest_block(request)
    epoch = get_epoch_containing_block(block_number)
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