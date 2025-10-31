from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar, Generic

from bittensor_wallet import Wallet
from turbobt.client import Bittensor
from turbobt.neuron import Neuron as TurboBtNeuron
from turbobt.subnet import (
    CertificateAlgorithm as TurboBtCertificateAlgorithm,
)
from turbobt.subnet import (
    NeuronCertificate as TurboBtNeuronCertificate,
)
from turbobt.subnet import (
    NeuronCertificateKeypair as TurboBtNeuronCertificateKeypair,
)
from turbobt.substrate.exceptions import UnknownBlock

from pylon.service.bittensor.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    BlockHash,
    CertificateAlgorithm,
    Coldkey,
    Hotkey,
    Metagraph,
    Neuron,
    NeuronCertificate,
    NeuronCertificateKeypair,
    PrivateKey,
    PublicKey,
    RevealRound,
    SubnetHyperparams,
    WeightsMapping,
)

logger = logging.getLogger(__name__)


class AbstractBittensorClient(ABC):
    """
    Interface for Bittensor clients.
    """

    def __init__(self, wallet: Wallet, uri: str):
        self.wallet = wallet
        self.uri = uri

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @abstractmethod
    async def open(self) -> None:
        """
        Opens the client and prepares it for work.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Closes the client and cleans up resources.
        """

    @abstractmethod
    async def get_block(self, number: int) -> Block | None:
        """
        Fetches a block from bittensor.
        """

    @abstractmethod
    async def get_latest_block(self) -> Block:
        """
        Fetches the latest block.
        """

    @abstractmethod
    async def get_neurons(self, netuid: int, block: Block) -> list[Neuron]:
        """
        Fetches all neurons at the given block.
        """

    @abstractmethod
    async def get_hyperparams(self, netuid: int, block: Block) -> SubnetHyperparams | None:
        """
        Fetches subnet's hyperparameters at the given block.
        """

    @abstractmethod
    async def get_certificates(self, netuid: int, block: Block) -> dict[Hotkey, NeuronCertificate]:
        """
        Fetches certificates for all neurons in a subnet.
        """

    @abstractmethod
    async def get_certificate(
        self, netuid: int, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None:
        """
        Fetches certificate for a hotkey in a subnet. If no hotkey is provided, the hotkey of the client's wallet is
        used.
        """

    @abstractmethod
    async def generate_certificate_keypair(
        self, netuid: int, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        """
        Generate a certificate keypair for the app's wallet.
        """

    @abstractmethod
    async def commit_weights(self, netuid: int, weights: WeightsMapping) -> RevealRound:
        """
        Commits weights. Returns round number when weights have to be revealed.
        """

    @abstractmethod
    async def set_weights(self, netuid: int, weights: WeightsMapping) -> None:
        """
        Sets weights. Used instead of commit_weights for subnets with commit-reveal disabled.
        """

    @abstractmethod
    async def get_metagraph(self, netuid: int, block: Block) -> Metagraph:
        """
        Fetches metagraph for a subnet at the given block.
        """


class TurboBtClient(AbstractBittensorClient):
    """
    Adapter for turbobt client.
    """

    def __init__(self, wallet: Wallet, uri: str):
        super().__init__(wallet, uri)
        self._raw_client: Bittensor | None = None

    async def open(self) -> None:
        assert self._raw_client is None, "The client is already open."
        logger.info(f"Opening the TurboBtClient for {self.uri}")
        self._raw_client = Bittensor(wallet=self.wallet, uri=self.uri)
        await self._raw_client.__aenter__()

    async def close(self) -> None:
        assert self._raw_client is not None, "The client is already closed."
        logger.info(f"Closing the TurboBtClient for {self.uri}")
        await self._raw_client.__aexit__(None, None, None)
        self._raw_client = None

    async def get_block(self, number: int) -> Block | None:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Fetching the block with number {number} from {self.uri}")
        block_obj = await self._raw_client.block(number).get()
        if block_obj is None or block_obj.number is None:
            return None
        return Block(
            number=block_obj.number,
            hash=BlockHash(block_obj.hash),
        )

    async def get_latest_block(self) -> Block:
        logger.debug(f"Fetching the latest block from {self.uri}")
        return await self.get_block(-1)

    @staticmethod
    async def _translate_neuron(neuron: TurboBtNeuron) -> Neuron:
        return Neuron(
            uid=neuron.uid,
            coldkey=Coldkey(neuron.coldkey),
            hotkey=Hotkey(neuron.hotkey),
            active=neuron.active,
            axon_info=AxonInfo(
                ip=neuron.axon_info.ip, port=neuron.axon_info.port, protocol=AxonProtocol(neuron.axon_info.protocol)
            ),
            stake=neuron.stake,
            rank=neuron.rank,
            emission=neuron.emission,
            incentive=neuron.incentive,
            consensus=neuron.consensus,
            trust=neuron.trust,
            validator_trust=neuron.validator_trust,
            dividends=neuron.dividends,
            last_update=neuron.last_update,
            validator_permit=neuron.validator_permit,
            pruning_score=neuron.pruning_score,
        )

    async def get_neurons(self, netuid: int, block: Block) -> list[Neuron]:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Fetching neurons from subnet {netuid} at block {block.number}, {self.uri}")
        neurons = await self._raw_client.subnet(netuid).list_neurons(block_hash=block.hash)
        return [await self._translate_neuron(neuron) for neuron in neurons]

    async def get_hyperparams(self, netuid: int, block: Block) -> SubnetHyperparams | None:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Fetching hyperparams from subnet {netuid} at block {block.number}, {self.uri}")
        params = await self._raw_client.subnet(netuid).get_hyperparameters(block_hash=block.hash)
        if not params:
            return None
        return SubnetHyperparams(**params)

    @staticmethod
    async def _translate_certificate(certificate: TurboBtNeuronCertificate) -> NeuronCertificate:
        return NeuronCertificate(
            algorithm=CertificateAlgorithm(certificate["algorithm"]),
            public_key=PublicKey(certificate["public_key"]),
        )

    async def get_certificates(self, netuid: int, block: Block) -> dict[Hotkey, NeuronCertificate]:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Fetching certificates from subnet {netuid} at block {block.number}, {self.uri}")
        certificates = await self._raw_client.subnet(netuid).neurons.get_certificates(block_hash=block.hash)
        if not certificates:
            return {}
        return {
            Hotkey(hotkey): await self._translate_certificate(certificate)
            for hotkey, certificate in certificates.items()
        }

    async def get_certificate(
        self, netuid: int, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        hotkey = hotkey or self.wallet.hotkey.ss58_address
        logger.debug(
            f"Fetching certificate of {hotkey} hotkey from subnet {netuid} at block {block.number}, {self.uri}"
        )
        certificate = await self._raw_client.subnet(netuid).neuron(hotkey=hotkey).get_certificate(block_hash=block.hash)
        if certificate:
            certificate = await self._translate_certificate(certificate)
        return certificate

    @staticmethod
    async def _translate_certificate_keypair(keypair: TurboBtNeuronCertificateKeypair) -> NeuronCertificateKeypair:
        return NeuronCertificateKeypair(
            algorithm=CertificateAlgorithm(keypair["algorithm"]),
            public_key=PublicKey(keypair["public_key"]),
            private_key=PrivateKey(keypair["private_key"]),
        )

    async def generate_certificate_keypair(
        self, netuid: int, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Generating certificate on subnet {netuid} at {self.uri}")
        keypair = await self._raw_client.subnet(netuid).neurons.generate_certificate_keypair(
            algorithm=TurboBtCertificateAlgorithm(algorithm)
        )
        if keypair:
            keypair = await self._translate_certificate_keypair(keypair)
        return keypair

    async def _translate_weights(self, netuid: int, weights: WeightsMapping) -> dict[int, float]:
        translated_weights = {}
        missing = []
        latest_block = await self.get_latest_block()
        hotkey_to_uid = {n.hotkey: n.uid for n in await self.get_neurons(netuid, latest_block)}
        for hotkey, weight in weights.items():
            if hotkey in hotkey_to_uid:
                translated_weights[hotkey_to_uid[hotkey]] = weight
            else:
                missing.append(hotkey)
        if missing:
            logger.warning(
                "Some of the hotkeys passed for weight commitment are missing. "
                f"Weights will not be commited for the following hotkeys: {missing}."
            )
        return translated_weights

    async def commit_weights(self, netuid: int, weights: WeightsMapping) -> RevealRound:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Commiting weights on subnet {netuid} at {self.uri}")
        reveal_round = await self._raw_client.subnet(netuid).weights.commit(
            await self._translate_weights(netuid, weights)
        )
        return RevealRound(reveal_round)

    async def set_weights(self, netuid: int, weights: WeightsMapping) -> None:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Setting weights on subnet {netuid} at {self.uri}")
        await self._raw_client.subnet(netuid).weights.set(await self._translate_weights(netuid, weights))

    async def get_metagraph(self, netuid: int, block: Block) -> Metagraph:
        neurons = await self.get_neurons(netuid, block)
        return Metagraph(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})


SubClient = TypeVar('SubClient', bound=AbstractBittensorClient)


class BittensorClient(Generic[SubClient], AbstractBittensorClient):
    """
    Bittensor client with archive node fallback support.

    This is a wrapper that delegates to two underlying
    client instances (main and archive) and handles fallback logic.
    """

    def __init__(
        self,
        wallet: Wallet,
        uri: str,
        archive_uri: str,
        archive_blocks_cutoff: int = 300,
        subclient_cls: type[SubClient] = TurboBtClient,
    ):
        super().__init__(wallet, uri)
        self.archive_uri = archive_uri
        self._archive_blocks_cutoff = archive_blocks_cutoff
        self.subclient_cls = subclient_cls
        self._main_client: SubClient = self.subclient_cls(wallet, uri)
        self._archive_client: SubClient = self.subclient_cls(wallet, archive_uri)

    async def open(self) -> None:
        await self._main_client.open()
        await self._archive_client.open()

    async def close(self) -> None:
        await self._main_client.close()
        await self._archive_client.close()

    async def get_block(self, number: int) -> Block | None:
        return await self._main_client.get_block(number)

    async def get_latest_block(self) -> Block:
        return await self._main_client.get_latest_block()

    async def get_neurons(self, netuid: int, block: Block) -> list[Neuron]:
        return await self._archive_fallback(self.subclient_cls.get_neurons, netuid=netuid, block=block)

    async def get_hyperparams(self, netuid: int, block: Block) -> SubnetHyperparams | None:
        return await self._archive_fallback(self.subclient_cls.get_hyperparams, netuid=netuid, block=block)

    async def get_certificates(self, netuid: int, block: Block) -> dict[Hotkey, NeuronCertificate]:
        return await self._archive_fallback(self.subclient_cls.get_certificates, netuid=netuid, block=block)

    async def get_certificate(
        self, netuid: int, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None:
        return await self._archive_fallback(self.subclient_cls.get_certificate, netuid=netuid, block=block, hotkey=hotkey)

    async def generate_certificate_keypair(
        self, netuid: int, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        return await self._main_client.generate_certificate_keypair(netuid, algorithm)

    async def commit_weights(self, netuid: int, weights: WeightsMapping) -> RevealRound:
        return await self._main_client.commit_weights(netuid, weights)

    async def set_weights(self, netuid: int, weights: WeightsMapping) -> None:
        return await self._main_client.set_weights(netuid, weights)

    async def get_metagraph(self, netuid: int, block: Block) -> Metagraph:
        neurons = await self.get_neurons(netuid, block)
        return Metagraph(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})

    async def _archive_fallback(self, operation: Callable, *args, block: Block, **kwargs):
        """
        Execute operation with automatic archive node fallback.
        """
        kwargs["block"] = block
        latest_block = await self.get_latest_block()
        if latest_block.number - block.number > self._archive_blocks_cutoff:
            logger.debug(f"Block is stale, falling back to the archive client: {self._archive_client.uri}")
            return await operation(self._archive_client, *args, **kwargs)

        try:
            return await operation(self._main_client, *args, **kwargs)
        except UnknownBlock:
            logger.warning(
                f"Block unknown for the main client, falling back to the archive client: {self._archive_client.uri}"
            )
            return await operation(self._archive_client, *args, **kwargs)
