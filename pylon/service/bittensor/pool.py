import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Generic, Self, TypeVar

from bittensor_wallet import Wallet
from pydantic import BaseModel, ConfigDict

from pylon._internal.common.types import HotkeyName, WalletName
from pylon.service.bittensor.client import AbstractBittensorClient, BittensorClient

logger = logging.getLogger(__name__)


class BittensorClientPoolClosed(Exception):
    pass


class BittensorClientPoolClosing(Exception):
    pass


class WalletKey(BaseModel):
    """
    Unique identifier for a wallet configuration.
    """

    wallet_name: WalletName | None
    hotkey_name: HotkeyName | None
    path: str | None

    model_config = ConfigDict(frozen=True)


BTClient = TypeVar("BTClient", bound=AbstractBittensorClient)


class BittensorClientPool(Generic[BTClient]):
    """
    Pool from which bittensor clients can be acquired based on the provided wallet.
    One client is shared for the same wallet.
    Once the client is opened, connection is maintained until the pool itself is closed.
    The pool is concurrency safe, but not thread safe.
    When the pool closes, first it waits for all the acquired clients to be released,
    then closes the clients gracefully.
    """

    def __init__(self, client_cls: type[BTClient] = BittensorClient, **client_kwargs) -> None:
        if "wallet" in client_kwargs:
            raise ValueError("Wallet may not be given as a client kwarg in the client pool.")
        self.is_open = False
        self.closing_state = False
        self.client_cls = client_cls
        self._pool: dict[WalletKey | None, BTClient] = {}
        self._close_condition = asyncio.Condition()
        self._acquire_lock = asyncio.Lock()
        self._acquire_counter = 0
        self.client_kwargs = client_kwargs

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Let the pending acquires happen first so that the acquire counter is not incremented too late.
        await self.close()

    async def open(self):
        await self.assert_not_closing()
        logger.info(f"Opening {self.client_cls.__name__} client pool.")
        self.is_open = True

    async def close(self):
        await self.assert_not_closing()
        await self.assert_not_closed()
        logger.info(f"Closing sequence initialized for {self.client_cls.__name__} client pool.")
        logger.info("Waiting for acquire lock before entering closing state...")
        async with self._acquire_lock:
            self.closing_state = True
            logger.info(
                f"Entered the closing state. Waiting until all ({self._acquire_counter}) clients "
                "are returned to the pool..."
            )
        async with self._close_condition:
            await self._close_condition.wait_for(self.can_close)
        logger.info("Closing all the clients...")
        await asyncio.gather(*(client.close() for client in self._pool.values()), return_exceptions=True)
        self.is_open = False
        self.closing_state = False
        self._pool.clear()
        logger.info(f"{self.client_cls.__name__} client pool successfully closed.")

    def can_close(self) -> bool:
        return self._acquire_counter == 0

    async def assert_not_closing(self):
        if self.closing_state:
            raise BittensorClientPoolClosing("The pool is currently closing.")

    async def assert_not_closed(self):
        if not self.is_open:
            raise BittensorClientPoolClosed("The pool is closed.")

    @asynccontextmanager
    async def acquire(self, wallet: Wallet | None) -> AsyncGenerator[BTClient]:
        """
        Acquire an instance of a bittensor client with connection ready.
        The client will use the provided wallet to perform requests.
        Acquiring task MUST NOT close the client as it may break other tasks that use the same client instance.

        Warning: Do not await for the pool to close from inside this context manager as this may cause a deadlock!

        Raises:
            BittensorClientPoolClosed: When acquire is called when the pool is closed.
            BittensorClientPoolClosing: When acquire is called when the pool is closing.
        """
        wallet_key = wallet and WalletKey(
            wallet_name=WalletName(wallet.name),
            hotkey_name=HotkeyName(wallet.hotkey_str),
            path=wallet.path,
        )
        wallet_name = f"'{wallet.name}'" if wallet else "no"
        async with self._acquire_lock:
            await self.assert_not_closing()
            await self.assert_not_closed()
            self._acquire_counter += 1
            logger.debug(
                f"Acquiring client with {wallet_name} wallet from the pool. "
                f"Count of clients acquired: {self._acquire_counter}"
            )
            if wallet_key in self._pool:
                client = self._pool[wallet_key]
            else:
                logger.debug(f"New client open with {wallet_name} wallet.")
                client = self._pool[wallet_key] = self.client_cls(wallet, **self.client_kwargs)
                await client.open()
        try:
            yield client
        finally:
            async with self._close_condition:
                self._acquire_counter -= 1
                logger.debug(
                    f"Returning client with {wallet_name} wallet to the pool. "
                    f"Count of clients acquired: {self._acquire_counter}"
                )
                self._close_condition.notify_all()
