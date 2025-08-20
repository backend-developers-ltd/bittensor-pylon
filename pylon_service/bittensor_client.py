import asyncio
import contextvars
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any

from bittensor_wallet import Wallet
from litestar.app import Litestar
from turbobt.client import Bittensor
from turbobt.substrate.exceptions import UnknownBlock

from pylon_common.models import Hotkey, Metagraph, Neuron
from pylon_common.settings import Settings, settings
from pylon_service.db import get_uid_weights_dict

logger = logging.getLogger(__name__)

bittensor_context: contextvars.ContextVar[Bittensor] = contextvars.ContextVar("bittensor")


def archive_fallback(func):
    """Decorator that determines what bittensor client to use and retries with archive client on UnknownBlock exceptions.

    Args:
        block_param_index: index of the block parameter in the function's positional arguments (after app).
    """

    async def wrapper(app, *args, **kwargs):
        block = kwargs.get("block", None)

        use_archive = (
            block is not None
            and app.state.latest_block is not None
            and app.state.latest_block - block > settings.bittensor_archive_blocks_cutoff
        )

        try:
            bittensor_context.set(app.state.archive_bittensor_client if use_archive else app.state.bittensor_client)
            return await func(app, *args, **kwargs)
        except UnknownBlock:
            if not use_archive:
                bittensor_context.set(app.state.archive_bittensor_client)
                logger.warning(f"UnknownBlock in {func.__name__}, retrying with archive client")
                return await func(app, *args, **kwargs)
            else:
                raise

    return wrapper


def get_bt_wallet(settings: Settings):
    try:
        wallet = Wallet(
            name=settings.bittensor_wallet_name,
            hotkey=settings.bittensor_wallet_hotkey_name,
            path=settings.bittensor_wallet_path,
        )
        return wallet
    except Exception as e:
        logger.error(f"Failed to create wallet: {e}")
        raise


async def create_bittensor_clients() -> tuple[Bittensor, Bittensor]:
    """Creates both main and archive Bittensor clients.

    Returns:
        tuple[Bittensor, Bittensor]: (main_client, archive_client)
    """
    wallet = get_bt_wallet(settings)
    main_network = settings.bittensor_network
    archive_network = settings.bittensor_archive_network
    try:
        main_client = Bittensor(wallet=wallet, uri=main_network)
        archive_client = Bittensor(wallet=wallet, uri=archive_network)
        return main_client, archive_client
    except Exception as e:
        logger.error(f"Failed to create Bittensor clients: {e}")
        raise


@archive_fallback
async def cache_metagraph(app: Litestar, *, block: int, block_hash: str):
    client = bittensor_context.get()
    neurons = await client.subnet(settings.bittensor_netuid).list_neurons(block_hash=block_hash)  # type: ignore

    neurons = [Neuron.model_validate(asdict(neuron)) for neuron in neurons]
    neurons = {neuron.hotkey: neuron for neuron in neurons}
    metagraph = Metagraph(block=block, block_hash=block_hash, neurons=neurons)
    app.state.metagraph_cache[block] = metagraph


@archive_fallback
async def get_block_timestamp(app: Litestar, *, block: int) -> datetime | None:
    """
    Fetches the creation timestamp for a specific block.
    """
    client = bittensor_context.get()
    try:
        block_obj = await client.block(block).get()
        return await block_obj.get_timestamp()
    except Exception as e:
        logger.error(f"Failed to fetch timestamp for block {block}: {e}")
        return None


@archive_fallback
async def get_metagraph(app: Litestar, *, block: int) -> Metagraph:
    if block not in app.state.metagraph_cache:
        client = bittensor_context.get()
        block_obj = await client.block(block).get()
        if block_obj is None or block_obj.number is None:
            raise ValueError(f"Block {block} not found in the blockchain.")
        await cache_metagraph(app, block=block_obj.number, block_hash=block_obj.hash)

    return app.state.metagraph_cache[block]


async def get_weights(app: Litestar, block: int) -> dict[int, float]:
    """
    Fetches the latest weights from the database for the current epoch.
    """
    # Get neurons from the metagraph
    metagraph = await get_metagraph(app, block=block)
    # TODO: check if neurons = metagraph.get_active_neurons() is needed instead
    neurons = metagraph.get_neurons()

    # Fetch neurons weights from db for the current epoch
    epoch = app.state.current_epoch_start
    if epoch is None:
        logger.warning("Epoch not available in app state. Cannot fetch db weights.")
        return {}

    weights = await get_uid_weights_dict(neurons, epoch)
    logger.info(f"Current db weights for epoch {epoch}: {weights}")
    return weights


async def commit_weights(app: Litestar, weights: dict[int, float]):
    """
    Commits weights to the subnet.
    """
    try:
        bt_client: Bittensor = app.state.bittensor_client
        subnet = bt_client.subnet(settings.bittensor_netuid)
        reveal_round = await subnet.weights.commit(weights)
        return reveal_round
    except Exception as e:
        logger.error(f"Failed to commit weights: {e}", exc_info=True)
        raise


# TODO: fix last_update fetching or replace with CRV3WeightsCommitted ?
async def fetch_last_weight_commit_block(app: Litestar) -> int | None:
    """
    Fetches the block number of the last successful weight commitment
    """
    return 0
    # hotkey = settings.bittensor_wallet_hotkey_name
    # metagraph = await get_metagraph(app, app.state.latest_block)
    # neuron = metagraph.get_neuron(hotkey)
    #
    # if neuron is None:
    #     logger.error(f"Neuron for own hotkey {hotkey} not found in the latest metagraph.")
    #     return None
    #
    # return neuron.last_update


@archive_fallback
async def get_commitment(app: Litestar, hotkey: Hotkey, *, block: int | None = None) -> str | None:
    """
    Fetches a specific commitment (as hex) for a hotkey, optionally at a given block.
    Uses netuid from settings and block_hash from metagraph cache.
    """
    netuid = settings.bittensor_netuid
    block_hash = app.state.metagraph_cache.get(block).block_hash
    client = bittensor_context.get()
    commitment = await client.subnet(netuid).commitments.get(hotkey, block_hash=block_hash)

    return commitment.hex() if commitment is not None else None


@archive_fallback
async def get_commitments(app: Litestar, *, block: int | None = None) -> dict[Hotkey, str]:
    """
    Fetches all commitments (hotkey: commitment_hex) for the configured subnet.
    Optionally uses a specific block_hash.
    """
    netuid = settings.bittensor_netuid
    block_hash = app.state.metagraph_cache.get(block).block_hash
    client = bittensor_context.get()
    commitments = await client.subnet(netuid).commitments.fetch(block_hash=block_hash)

    if commitments is None:
        return {}
    return {hotkey: data.hex() for hotkey, data in commitments.items()}


async def set_commitment(app: Litestar, data: bytes, timeout: int = 30):
    """
    Sets a commitment (hex string).
    """
    netuid = settings.bittensor_netuid
    bt_client: Bittensor = app.state.bittensor_client
    extrinsic = await bt_client.subnet(netuid).commitments.set(data=data)
    print(f"extrinsic: {extrinsic}")
    async with asyncio.timeout(timeout):
        await extrinsic.wait_for_finalization()


async def set_hyperparam(app: Litestar, name: str, value: Any, timeout: int = 30):
    """
    Sets a hyperparameter on the subnet by dispatching to the correct sudo function.
    """
    netuid = settings.bittensor_netuid
    bt_client: Bittensor = app.state.bittensor_client
    wallet = get_bt_wallet(settings)

    try:
        extrinsic = None
        if name == "tempo":
            extrinsic = await bt_client.subtensor.admin_utils.sudo_set_tempo(netuid, int(value), wallet)
        elif name == "weights_set_rate_limit":
            extrinsic = await bt_client.subtensor.admin_utils.sudo_set_weights_set_rate_limit(
                netuid, int(value), wallet
            )
        elif name == "commit_reveal_weights_enabled":
            extrinsic = await bt_client.subtensor.admin_utils.sudo_set_commit_reveal_weights_enabled(
                netuid, bool(value), wallet
            )
        else:
            raise Exception(f"Hyperparameter '{name}' is not supported for modification.")

        async with asyncio.timeout(timeout):
            await extrinsic.wait_for_finalization()

        logger.info(f"Successfully set hyperparameter '{name}' to '{value}'.")
        return

    except TimeoutError:
        raise Exception(f"Timed out setting hyperparameter '{name}' after {timeout} seconds.")
    except Exception as e:
        raise Exception(f"Failed to set hyperparameter '{name}' - an unexpected error occurred: {e}")
