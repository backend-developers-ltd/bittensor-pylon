from litestar import get, Request
from app.bittensor_client import get_metagraph
from app.settings import settings
import logging
import functools
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
            return {"detail": error_message, "status_code": 500}

    return wrapper


@get("/latest_block")
@safe_endpoint
async def latest_block(request: Request) -> dict:
    block = request.app.state.latest_block
    if block is None:
        return {"detail": "Latest block not available - try again later", "status_code": 503}
    return {"block": block}


@get("/metagraph")
@safe_endpoint
async def latest_metagraph(request: Request) -> dict:
    block = request.app.state.latest_block
    if block is None:
        return {"detail": "Latest block not available - try again later", "status_code": 503}
    metagraph = request.app.state.metagraph_cache.get(block)
    return metagraph.model_dump()


@get("/block_hash/{block_number:int}")
@safe_endpoint
async def block_hash(request: Request, block_number: int) -> dict:
    metagraph = await get_metagraph(request.app, block_number)
    return metagraph.block_hash


@get("/epoch/{block_number:int}")
@safe_endpoint
async def epoch(block_number: int) -> dict:
    epoch = get_epoch_containing_block(block_number, settings.bittensor_netuid)
    return epoch.model_dump()


@get("/metagraph/{block_number:int}")
@safe_endpoint
async def metagraph(request: Request, block_number: int) -> dict:
    metagraph = await get_metagraph(request.app, block_number)
    return metagraph.model_dump()
