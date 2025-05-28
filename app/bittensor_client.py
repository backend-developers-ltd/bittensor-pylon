from turbobt.client import Bittensor
from app.settings import settings, Settings
import logging
from bittensor_wallet import Wallet
from app.models import Metagraph, Neuron
from turbobt.block import Block
from dataclasses import fields

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


# TODO: this should not be necessary
def _block_hash_to_bytes(block_hash: str | bytes) -> bytes:
    if isinstance(block_hash, str) and block_hash.startswith("0x"):
        return bytes.fromhex(block_hash[2:])
    elif isinstance(block_hash, str):
        return bytes.fromhex(block_hash)
    return block_hash  # assume already bytes


# TODO: this function should be moved in turbobt
def _neuron_to_dict(neuron: Neuron) -> dict:
    return {f.name: getattr(neuron, f.name) for f in fields(neuron)}  # type: ignore


async def cache_metagraph(app, client: Bittensor, block: Block):
    block_hash_bytes = _block_hash_to_bytes(block.hash)
    neurons = await client.subnet(settings.bittensor_netuid).list_neurons(block_hash=block_hash_bytes)  # type: ignore
    block_number = block.number
    if type(block_number) is not int:
        raise ValueError("Block number is not an integer")
    neurons = [Neuron.model_validate(_neuron_to_dict(neuron)) for neuron in neurons]
    metagraph = Metagraph(block=block_number, block_hash=block.hash, neurons=neurons)
    app.state.metagraph_cache[block_number] = metagraph


async def get_metagraph(app, block_number: int) -> Metagraph:
    if block_number not in app.state.metagraph_cache:
        async with app.state.bittensor_client.block(block_number) as block:
            await cache_metagraph(app, app.state.bittensor_client, block)
    return app.state.metagraph_cache[block_number]
