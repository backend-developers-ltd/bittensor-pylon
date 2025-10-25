"""
Mock Bittensor client for testing API endpoints.

This module provides a mock implementation of AbstractBittensorClient that can be configured
to return specific values or raise exceptions, enabling comprehensive testing of API endpoints
without requiring actual blockchain interactions.
"""

from collections import defaultdict
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, TypeAlias

from bittensor_wallet import Wallet

from pylon.service.bittensor.client import AbstractBittensorClient
from pylon.service.bittensor.models import (
    Block,
    CertificateAlgorithm,
    Hotkey,
    Neuron,
    NeuronCertificate,
    NeuronCertificateKeypair,
    RevealRound,
    SubnetHyperparams,
    WeightsMapping,
)

Behavior: TypeAlias = Callable | Exception | Any
MethodName: TypeAlias = str
Call: TypeAlias = tuple


class MockBittensorClient(AbstractBittensorClient[None]):
    """
    Mock implementation of AbstractBittensorClient for testing.

    This client allows tests to configure behavior through context manager that define
    how each method should behave (return values, exceptions, etc.).

    Each method maintains a queue of behaviors that are consumed in order.

    Example usage:
        mock_client = MockBittensorClient()
        async with mock_client.mock_behavior(
            get_certificates=[
                {"5FHneW46...": NeuronCertificate(...)},
                {"5GHneW47...": NeuronCertificate(...)},
            ],
            get_latest_block=[Block(number=100, hash=BlockHash("0x123"))]
        ):
            # First call returns first item, second call returns second item, etc.
            result1 = await mock_client.get_certificates(1)
            result2 = await mock_client.get_certificates(1)
    """

    def __init__(self, wallet: Wallet | None = None, uri: str = "mock://test"):
        super().__init__(wallet=wallet or Wallet(), uri=uri)
        self._behaviors: dict[MethodName, list[Behavior]] = defaultdict(list)
        self._is_open = False

        # Track method calls for assertion in tests
        self.calls: dict[MethodName, list[Call]] = defaultdict(list)

    async def open(self) -> None:
        self._is_open = True

    async def close(self) -> None:
        self._is_open = False

    @asynccontextmanager
    async def mock_behavior(self, **behaviors: list[Behavior] | Behavior):
        """
        Async context manager to configure mock behavior for methods.

        Args:
            **behaviors: Method names as keys, and either:
                - A list of behaviors (each can be a callable, value, or exception)
                - A single behavior (callable, value, or exception)

        Each behavior can be:
            - A callable that will be called with the method's arguments
            - A value to be returned directly
            - An exception instance to be raised

        Example:
            async with mock_client.mock_behavior(
                get_latest_block=[Block(number=100, hash=BlockHash("0x123"))],
                get_certificates=[
                    lambda netuid, block: {...},
                    {"hotkey": NeuronCertificate(...)},
                ],
                get_certificate=[None, Exception("Network error")]
            ):
                # Test code here
        """
        for method_name, behavior in behaviors.items():
            if not isinstance(behavior, list):
                self._behaviors[method_name].append(behavior)
            else:
                self._behaviors[method_name].extend(behavior)

        try:
            yield
        finally:
            self._behaviors.clear()

    async def _execute_behavior(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute the next configured behavior for a method.

        Args:
            method_name: Name of the method
            *args: Positional arguments passed to the method
            **kwargs: Keyword arguments passed to the method

        Returns:
            The result of the configured behavior

        Raises:
            Exception: If the behavior is configured to raise an exception
            NotImplementedError: If no behavior is configured for the method
        """
        if not self._behaviors[method_name]:
            raise NotImplementedError(
                f"No mock behavior configured for {method_name}. Use mock_behavior() context manager to configure it."
            )

        # Get the next behavior from the queue
        behavior = self._behaviors[method_name].pop(0)

        if isinstance(behavior, Exception):
            raise behavior

        if callable(behavior):
            return behavior(*args, **kwargs)

        return behavior

    async def get_block(self, number: int) -> Block | None:
        """
        Get a block by number.
        """
        self.calls["get_block"].append((number,))
        return await self._execute_behavior("get_block", number)

    async def get_latest_block(self) -> Block:
        """
        Get the latest block.
        """
        self.calls["get_latest_block"].append(())
        return await self._execute_behavior("get_latest_block")

    async def _get_neurons(self, netuid: int, block: Block | None = None) -> list[Neuron]:
        """
        Get neurons for a subnet.
        """
        self.calls["_get_neurons"].append((netuid, block))
        return await self._execute_behavior("_get_neurons", netuid, block)

    async def _get_hyperparams(self, netuid: int, block: Block | None = None) -> SubnetHyperparams | None:
        """
        Get hyperparameters for a subnet.
        """
        self.calls["_get_hyperparams"].append((netuid, block))
        return await self._execute_behavior("_get_hyperparams", netuid, block)

    async def _get_certificates(self, netuid: int, block: Block | None = None) -> dict[Hotkey, NeuronCertificate]:
        """
        Get all certificates for a subnet.
        """
        self.calls["_get_certificates"].append((netuid, block))
        return await self._execute_behavior("_get_certificates", netuid, block)

    async def _get_certificate(
        self, netuid: int, hotkey: Hotkey | None = None, block: Block | None = None
    ) -> NeuronCertificate | None:
        """
        Get a certificate for a specific hotkey.
        """
        self.calls["_get_certificate"].append((netuid, hotkey, block))
        return await self._execute_behavior("_get_certificate", netuid, hotkey, block)

    async def generate_certificate_keypair(
        self, netuid: int, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        """
        Generate a certificate keypair.
        """
        self.calls["generate_certificate_keypair"].append((netuid, algorithm))
        return await self._execute_behavior("generate_certificate_keypair", netuid, algorithm)

    async def commit_weights(self, netuid: int, weights: WeightsMapping) -> RevealRound:
        """
        Commit weights for a subnet.
        """
        self.calls["commit_weights"].append((netuid, weights))
        return await self._execute_behavior("commit_weights", netuid, weights)

    async def set_weights(self, netuid: int, weights: WeightsMapping) -> None:
        """
        Set weights for a subnet.
        """
        self.calls["set_weights"].append((netuid, weights))
        return await self._execute_behavior("set_weights", netuid, weights)

    async def reset_call_tracking(self) -> None:
        """
        Reset all call tracking.
        """
        self.calls.clear()
