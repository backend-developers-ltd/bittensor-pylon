import asyncio

import pytest
import pytest_asyncio
from bittensor_wallet import Wallet

from pylon._internal.common.types import HotkeyName, WalletName
from pylon.service.bittensor.client import BittensorClient
from pylon.service.bittensor.pool import (
    BittensorClientPool,
    BittensorClientPoolInvalidState,
    WalletKey,
)
from tests.helpers import wait_until


@pytest_asyncio.fixture
async def barrier_factory():
    barriers = []

    async def _create_barrier(parties: int):
        barrier = asyncio.Barrier(parties)
        barriers.append(barrier)
        return barrier

    try:
        yield _create_barrier
    finally:
        for barrier in barriers:
            if not barrier.broken:
                await barrier.abort()


async def acquire_client(
    pool: BittensorClientPool[BittensorClient], wallet: Wallet | None, barrier: asyncio.Barrier
) -> BittensorClient:
    async with pool.acquire(wallet=wallet) as client:
        await barrier.wait()
    return client


@pytest.mark.asyncio
async def test_bittensor_client_pool_proper_use(barrier_factory):
    """
    The general plan of this test is to test normal use scenario:
        - spawn 5 tasks that just acquire the client from the pool
          and waits for the signal form the barrier to release them,
        - close the client and see if it withholds its closure until all clients are returned to the pool,
        - return the clients to the pool,
        - check if everything is clean.
    """
    barrier = await barrier_factory(6)
    # These wallets should produce the same client even though wallet1 != wallet2
    wallets = [Wallet(), Wallet()]
    # Spawn 5 tasks that will wait with the client acquired.
    pool = BittensorClientPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    assert pool.state == BittensorClientPool.State.OPEN
    tasks = [asyncio.create_task(acquire_client(pool, wallets[i % 2], barrier)) for i in range(5)]
    # Wait until all the tasks acquire the client
    await wait_until(lambda: barrier.n_waiting == barrier.parties - 1)
    assert pool._acquire_counter == 5
    # Acquire the client and check its attributes.
    async with pool.acquire(wallet=wallets[0]) as client_wallet:
        assert pool._pool == {
            WalletKey(  # type: ignore[reportUnhashable]
                wallet_name=WalletName("default"), hotkey_name=HotkeyName("default"), path="~/.bittensor/wallets/"
            ): client_wallet
        }
        assert pool._acquire_counter == 6
        assert client_wallet.uri == pool.client_kwargs["uri"]
        assert client_wallet.archive_uri == pool.client_kwargs["archive_uri"]
        # Check if the client is open
        assert client_wallet._main_client._raw_client is not None
        assert client_wallet._archive_client._raw_client is not None
    assert pool._acquire_counter == 5
    # Check if you can acquire client without wallet
    async with pool.acquire(wallet=None) as client_no_wallet:
        assert pool._pool == {
            WalletKey(  # type: ignore[reportUnhashable]
                wallet_name=WalletName("default"), hotkey_name=HotkeyName("default"), path="~/.bittensor/wallets/"
            ): client_wallet,
            None: client_no_wallet,
        }
        assert pool._acquire_counter == 6
    assert pool._acquire_counter == 5
    close_task = asyncio.create_task(pool.close())
    # See if close() will put the pool into the closing state, but wait with closure until all clients are returned to
    # the pool.
    await wait_until(lambda: pool.state == BittensorClientPool.State.CLOSING)
    # Release the tasks so that the pool may close.
    async with asyncio.timeout(2):
        await barrier.wait()
    clients = await asyncio.gather(*tasks)
    # Check if all the tasks clients were the same instance.
    assert set(clients) == {client_wallet}
    assert pool._acquire_counter == 0
    await close_task
    # Check if the pool is closed properly.
    assert pool.state == BittensorClientPool.State.CLOSED
    assert pool._pool == {}
    # Check if the client is closed properly.
    assert client_wallet._main_client._raw_client is None
    assert client_wallet._archive_client._raw_client is None


@pytest.mark.asyncio
async def test_bittensor_client_pool_acquire_when_pool_closed():
    """
    Test that acquiring a client from a closed pool raises BittensorClientPoolClosed.
    """
    pool = BittensorClientPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    with pytest.raises(BittensorClientPoolInvalidState):
        async with pool.acquire(wallet=None):
            pass


@pytest.mark.asyncio
async def test_bittensor_client_pool_acquire_when_pool_closing(barrier_factory):
    """
    Test that acquiring a client while pool is closing raises BittensorClientPoolClosing.
    """
    barrier = await barrier_factory(2)
    pool = BittensorClientPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    task = asyncio.create_task(acquire_client(pool, None, barrier))
    await wait_until(lambda: pool._acquire_counter == 1)
    close_task = asyncio.create_task(pool.close())
    await wait_until(lambda: pool.state == BittensorClientPool.State.CLOSING)
    with pytest.raises(BittensorClientPoolInvalidState):
        async with pool.acquire(wallet=None):
            pass
    async with asyncio.timeout(2):
        await barrier.wait()
    await task
    await close_task


@pytest.mark.asyncio
async def test_bittensor_client_pool_close_already_closed_pool():
    """
    Test that closing an already closed pool raises BittensorClientPoolClosed.
    """
    pool = BittensorClientPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    with pytest.raises(BittensorClientPoolInvalidState):
        await pool.close()


@pytest.mark.asyncio
async def test_bittensor_client_pool_close_pool_while_closing(barrier_factory):
    """
    Test that closing a pool while it's already closing raises BittensorClientPoolClosing.
    """
    barrier = await barrier_factory(2)
    pool = BittensorClientPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    task = asyncio.create_task(acquire_client(pool, None, barrier))
    await wait_until(lambda: pool._acquire_counter == 1)
    close_task = asyncio.create_task(pool.close())
    await wait_until(lambda: pool.state == BittensorClientPool.State.CLOSING)
    with pytest.raises(BittensorClientPoolInvalidState):
        await pool.close()
    async with asyncio.timeout(2):
        await barrier.wait()
    await task
    await close_task


@pytest.mark.asyncio
async def test_bittensor_client_pool_close_empty_pool():
    """
    Test closing already empty pool.
    """
    pool = BittensorClientPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    assert pool.state == BittensorClientPool.State.OPEN
    await pool.close()
    assert pool.state == BittensorClientPool.State.CLOSED


@pytest.mark.asyncio
async def test_bittensor_client_pool_stress(barrier_factory):
    """
    Pool's stress test.
    """
    barrier = await barrier_factory(10000)
    pool = BittensorClientPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    tasks = [asyncio.create_task(acquire_client(pool, None, barrier)) for _ in range(10000)]
    async with asyncio.timeout(2):
        clients = await asyncio.gather(*tasks)
    await pool.close()
    assert set(clients) == {clients[0]}


@pytest.mark.asyncio
async def test_bittensor_client_pool_close_timeout(barrier_factory):
    """
    Test that the pool will close after timeout.
    """
    barrier = await barrier_factory(2)
    pool = BittensorClientPool(
        pool_closing_timeout=0.1,
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    task = asyncio.create_task(acquire_client(pool, None, barrier))
    await wait_until(lambda: pool._acquire_counter == 1)
    await pool.close()
    async with asyncio.timeout(2):
        await barrier.wait()
    await task
    # Check if the client is closed.
    client = task.result()
    assert client._main_client._raw_client is None
    assert client._archive_client._raw_client is None
