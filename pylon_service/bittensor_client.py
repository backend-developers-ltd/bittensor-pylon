import asyncio
import contextvars
import logging
from dataclasses import asdict
from typing import Any

from bittensor_wallet import Wallet
from litestar.app import Litestar
from turbobt.client import Bittensor
from turbobt.subnet import CertificateAlgorithm as NeuronCertificateAlgorithm
from turbobt.subnet import NeuronCertificate
from turbobt.substrate.exceptions import UnknownBlock

from pylon_common.models import CertificateAlgorithm, Hotkey, Metagraph, Neuron
from pylon_common.settings import Settings, settings

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
async def get_metagraph(app: Litestar, *, block: int) -> Metagraph:
    if block not in app.state.metagraph_cache:
        client = bittensor_context.get()
        block_obj = await client.block(block).get()
        if block_obj is None or block_obj.number is None:
            raise ValueError(f"Block {block} not found in the blockchain.")
        await cache_metagraph(app, block=block_obj.number, block_hash=block_obj.hash)

    return app.state.metagraph_cache[block]


@archive_fallback
async def get_certificates(app: Litestar, *, block: int | None = None) -> dict[Hotkey, NeuronCertificate]:
    """
    Get all certificates for the configured subnet.

    Optionally uses a specific block_hash.
    """
    if block is not None:
        metagraph = await get_metagraph(app, block=block)
        block_hash = metagraph.block_hash
    else:
        block_hash = None

    client = bittensor_context.get()
    netuid = settings.bittensor_netuid
    certificates = await client.subnet(netuid).neurons.get_certificates(block_hash=block_hash)

    return {} if certificates is None else certificates


@archive_fallback
async def get_certificate(
    app: Litestar, hotkey: Hotkey | None = None, *, block: int | None = None
) -> NeuronCertificate | None:
    """
    Get a specific certificates for a hotkey.

    If the hotkey is not specified, the hotkey of the current wallet is used.
    Optionally uses a specific block_hash.
    """
    if block is not None:
        metagraph = await get_metagraph(app, block=block)
        block_hash = metagraph.block_hash
    else:
        block_hash = None

    client = bittensor_context.get()
    netuid = settings.bittensor_netuid

    if hotkey is None:
        hotkey = client.wallet.hotkey.ss58_address

    return await client.subnet(netuid).neuron(hotkey=hotkey).get_certificate(block_hash=block_hash)


@archive_fallback
async def generate_certificate_keypair(app: Litestar, algorithm: CertificateAlgorithm) -> NeuronCertificate | None:
    """
    Generate a certificate keypair for the app's wallet.
    """
    netuid = settings.bittensor_netuid
    client = bittensor_context.get()

    return await client.subnet(netuid).neurons.generate_certificate_keypair(
        algorithm=NeuronCertificateAlgorithm(algorithm)
    )


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
