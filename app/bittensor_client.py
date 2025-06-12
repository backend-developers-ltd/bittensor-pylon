import logging
from dataclasses import asdict

from bittensor_wallet import Wallet
from litestar.app import Litestar
from turbobt.block import Block
from turbobt.client import Bittensor

from app.db import get_neurons_weights
from app.models import Hotkey, Metagraph, Neuron
from app.settings import Settings, settings

logger = logging.getLogger(__name__)


def get_bt_wallet(settings: Settings):
    try:
        wallet = Wallet(
            name=settings.bittensor_wallet_name,
            hotkey=settings.bittensor_wallet_hotkey_name,
            path=settings.bittensor_wallet_path,
        )
        logger.info(f"Wallet created successfully for hotkey '{settings.bittensor_wallet_hotkey_name}'")
        return wallet
    except Exception as e:
        logger.error(f"Failed to create wallet: {e}")
        raise


async def create_bittensor_client() -> Bittensor:
    wallet = get_bt_wallet(settings)
    logger.info("Creating Bittensor client...")
    try:
        client = Bittensor(wallet=wallet)
        logger.info(f"Bittensor client created for wallet '{wallet}'")
        return client
    except Exception as e:
        logger.error(f"Failed to create Bittensor client: {e}")
        raise


async def cache_metagraph(app: Litestar, block: Block):
    neurons = await app.state.bittensor_client.subnet(settings.bittensor_netuid).list_neurons(block_hash=block.hash)  # type: ignore
    block_number = block.number
    if type(block_number) is not int:
        raise ValueError("Block number is not an integer")
    neurons = [Neuron.model_validate(asdict(neuron)) for neuron in neurons]
    neurons = {neuron.hotkey: neuron for neuron in neurons}
    metagraph = Metagraph(block=block_number, block_hash=block.hash, neurons=neurons)
    app.state.metagraph_cache[block_number] = metagraph


async def get_metagraph(app: Litestar, block_number: int) -> Metagraph:
    if block_number not in app.state.metagraph_cache:
        block = await app.state.bittensor_client.block(block_number).get()
        await cache_metagraph(app, block)
    return app.state.metagraph_cache[block_number]


async def get_weights(app: Litestar, block: int) -> dict[int, float]:
    """
    Fetches the latest weights from the database for the current epoch.
    """
    # Get neurons from the metagraph
    metagraph = app.state.metagraph_cache.get(block)
    neurons = metagraph.get_active_neurons()

    # Fetch neurons weights from db for the current epoch
    epoch = app.state.current_epoch_start
    if epoch is None:
        logger.warning("Epoch not available in app state. Cannot fetch db weights.")
        return None

    weights = await get_neurons_weights(neurons, epoch)
    logger.info(f"Current db weights for epoch {epoch}: {weights}")
    return weights


async def commit_weights(app: Litestar, weights: dict[Hotkey, float]):
    """
    Commits weights to the subnet.
    """
    try:
        bt_client: Bittensor = app.state.bittensor_client
        subnet = bt_client.subnet(settings.bittensor_netuid)
        reveal_round = await subnet.weights.commit(weights)
        logger.info(f"Successfully committed weights. Expected reveal round: {reveal_round}")
    except Exception as e:
        logger.error(f"Failed to commit weights: {e}", exc_info=True)
        raise


# TODO: replace with CRV3WeightsCommitted ? as last_update might not be reliable
async def fetch_last_weight_commit_block(app: Litestar) -> int | None:
    """
    Fetches the block number of the last successful weight commitment
    """
    hotkey = settings.bittensor_wallet_hotkey_name
    metagraph = await get_metagraph(app, app.state.latest_block)
    neuron = metagraph.get_neuron(hotkey)

    if neuron is None:
        logger.error(f"Neuron for own hotkey {hotkey} not found in the latest metagraph.")
        return None

    return neuron.last_update
