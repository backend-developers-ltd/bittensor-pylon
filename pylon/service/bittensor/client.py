from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

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

RawClient = TypeVar("RawClient")


logger = logging.getLogger(__name__)


class AbstractBittensorClient(Generic[RawClient], ABC):
    """
    Wrapper around other bittensor clients like turbobt.
    """

    def __init__(
        self,
        wallet: Wallet,
        uri: str,
        archive_blocks_cutoff: int = 300,
        archive_client: AbstractBittensorClient | None = None,
    ):
        self.wallet = wallet
        self.uri = uri
        self.archive_blocks_cutoff = archive_blocks_cutoff
        self.archive_client = archive_client
        self._raw_client: RawClient | None = None

    async def __aenter__(self):
        await self.open()
        if self.archive_client:
            await self.archive_client.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        if self.archive_client:
            await self.archive_client.close()

    @abstractmethod
    async def open(self) -> None:
        """
        Creates and opens the raw client and prepares other things needed for the client to work.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Closes the raw client and cleans up other things if needed.
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
    async def _get_neurons(self, netuid: int, block: Block | None = None) -> list[Neuron]:
        """
        Fetches all neurons at the given block.
        """

    @abstractmethod
    async def _get_hyperparams(self, netuid: int, block: Block | None = None) -> SubnetHyperparams | None:
        """
        Fetches subnet's hyperparameters at the given block.
        """

    @abstractmethod
    async def _get_certificates(self, netuid: int, block: Block | None = None) -> dict[Hotkey, NeuronCertificate]:
        """
        Fetches certificates for all neurons in a subnet.
        """

    @abstractmethod
    async def _get_certificate(
        self, netuid: int, hotkey: Hotkey | None = None, block: Block | None = None
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

    async def archive_fallback(self, method_name: str, *args, block: Block | None = None, **kwargs):
        """
        Decide whether the main node or the archive node should be queried and perform the method on the chosen one.

        Archive node should be queried when the query is performed for a block older than the latest block by
        `archive_blocks_cutoff`, usually it's 300 blocks old.
        Archive node is also used when the main node query fails due to unknown block error.
        """
        kwargs["block"] = block
        method = getattr(self, method_name)
        # We assume that block == None means "use the latest block", so fallback to archive should never be needed
        # in that case.
        if not self.archive_client or block is None:
            return await method(*args, **kwargs)
        archive_method = getattr(self.archive_client, method_name)
        latest_block = await self.get_latest_block()
        if latest_block.number - block.number > self.archive_blocks_cutoff:
            return await archive_method(*args, **kwargs)
        try:
            return await method(*args, **kwargs)
        except UnknownBlock:
            return await archive_method(*args, **kwargs)

    async def get_neurons(self, netuid: int, block: Block | None = None) -> list[Neuron]:
        return await self.archive_fallback("_get_neurons", netuid, block=block)

    async def get_hyperparams(self, netuid: int, block: Block | None = None) -> SubnetHyperparams | None:
        return await self.archive_fallback("_get_hyperparams", netuid, block=block)

    async def get_certificates(self, netuid: int, block: Block | None = None) -> dict[Hotkey, NeuronCertificate]:
        return await self.archive_fallback("_get_certificates", netuid, block=block)

    async def get_certificate(
        self, netuid: int, hotkey: Hotkey | None = None, block: Block | None = None
    ) -> NeuronCertificate | None:
        return await self.archive_fallback("_get_certificate", netuid, hotkey=hotkey, block=block)

    async def get_metagraph(self, netuid: int, block: Block) -> Metagraph:
        neurons = await self.get_neurons(netuid, block)
        return Metagraph(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})


class TurboBtClient(AbstractBittensorClient[Bittensor]):
    """
    Bittensor client that uses TurboBt as a backend.
    """

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
    async def translate_neuron(neuron: TurboBtNeuron) -> Neuron:
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

    async def _get_neurons(self, netuid: int, block: Block | None = None) -> list[Neuron]:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        block_num = block.number if block else "latest"
        logger.debug(f"Fetching neurons from subnet {netuid} at the {block_num} block, {self.uri}")
        block_hash = block and block.hash
        neurons = await self._raw_client.subnet(netuid).list_neurons(block_hash=block_hash)
        return [await self.translate_neuron(neuron) for neuron in neurons]

    async def _get_hyperparams(self, netuid: int, block: Block | None = None) -> SubnetHyperparams | None:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        block_num = block.number if block else "latest"
        logger.debug(f"Fetching hyperparams from subnet {netuid} at the {block_num} block, {self.uri}")
        block_hash = block and block.hash
        params = await self._raw_client.subnet(netuid).get_hyperparameters(block_hash=block_hash)
        if not params:
            return None
        return SubnetHyperparams(**params)

    @staticmethod
    async def translate_certificate(certificate: TurboBtNeuronCertificate) -> NeuronCertificate:
        return NeuronCertificate(
            algorithm=CertificateAlgorithm(certificate["algorithm"]),
            public_key=PublicKey(certificate["public_key"]),
        )

    async def _get_certificates(self, netuid: int, block: Block | None = None) -> dict[Hotkey, NeuronCertificate]:
        """
        Fetches certificates for all neurons in a subnet.
        """
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        block_num = block.number if block else "latest"
        logger.debug(f"Fetching certificates from subnet {netuid} at the {block_num} block, {self.uri}")
        block_hash = block and block.hash
        certificates = await self._raw_client.subnet(netuid).neurons.get_certificates(block_hash=block_hash)
        if not certificates:
            return {}
        return {
            Hotkey(hotkey): await self.translate_certificate(certificate)
            for hotkey, certificate in certificates.items()
        }

    async def _get_certificate(
        self, netuid: int, hotkey: Hotkey | None = None, block: Block | None = None
    ) -> NeuronCertificate | None:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        hotkey = hotkey or self.wallet.hotkey.ss58_address
        block_num = block.number if block else "latest"
        logger.debug(
            f"Fetching certificate of {hotkey} hotkey from subnet {netuid} at the {block_num} block, {self.uri}"
        )
        block_hash = block and block.hash
        certificate = await self._raw_client.subnet(netuid).neuron(hotkey=hotkey).get_certificate(block_hash=block_hash)
        if certificate:
            certificate = await self.translate_certificate(certificate)
        return certificate

    @staticmethod
    async def translate_certificate_keypair(keypar: TurboBtNeuronCertificateKeypair) -> NeuronCertificateKeypair:
        return NeuronCertificateKeypair(
            algorithm=CertificateAlgorithm(keypar["algorithm"]),
            public_key=PublicKey(keypar["public_key"]),
            private_key=PrivateKey(keypar["private_key"]),
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
            keypair = await self.translate_certificate_keypair(keypair)
        return keypair

    async def translate_weights(self, netuid: int, weights: WeightsMapping) -> dict[int, float]:
        translated_weights = {}
        missing = []
        hotkey_to_uid = {n.hotkey: n.uid for n in await self._get_neurons(netuid)}
        for hotkey, weight in weights.items():
            if hotkey in hotkey_to_uid:
                translated_weights[hotkey_to_uid[hotkey]] = weight
            else:
                missing.append(hotkey)
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
            await self.translate_weights(netuid, weights)
        )
        return RevealRound(reveal_round)

    async def set_weights(self, netuid: int, weights: WeightsMapping) -> None:
        assert self._raw_client is not None, (
            "The client is not open, please use the client as a context manager or call the open() method."
        )
        logger.debug(f"Setting weights on subnet {netuid} at {self.uri}")
        await self._raw_client.subnet(netuid).weights.set(await self.translate_weights(netuid, weights))
