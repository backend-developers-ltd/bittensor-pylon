import logging
from dataclasses import asdict

from bittensor_wallet import Wallet
from turbobt.block import Block
from turbobt.client import Bittensor

from app.models import Metagraph, Neuron
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


async def cache_metagraph(app, block: Block):
    neurons = await app.state.bittensor_client.subnet(settings.bittensor_netuid).list_neurons(block_hash=block.hash)  # type: ignore
    block_number = block.number
    if type(block_number) is not int:
        raise ValueError("Block number is not an integer")
    neurons = [Neuron.model_validate(asdict(neuron)) for neuron in neurons]
    metagraph = Metagraph(block=block_number, block_hash=block.hash, neurons=neurons)
    app.state.metagraph_cache[block_number] = metagraph


async def get_metagraph(app, block_number: int) -> Metagraph:
    if block_number not in app.state.metagraph_cache:
        block = await app.state.bittensor_client.block(block_number).get()
        await cache_metagraph(app, block)
    return app.state.metagraph_cache[block_number]
