"""
Shared fixtures for service endpoint tests.
"""

import pytest_asyncio
from litestar.testing import AsyncTestClient

from pylon._internal.common.types import IdentityName
from pylon.service.bittensor.pool import BittensorClientPool
from pylon.service.identities import identities
from tests.mock_bittensor_client import MockBittensorClient


@pytest_asyncio.fixture(loop_scope="session")
async def mock_bt_client_pool():
    """
    Create a mock Bittensor client pool.
    """
    async with BittensorClientPool(client_cls=MockBittensorClient, uri="ws://localhost:8000") as pool:
        yield pool


@pytest_asyncio.fixture
async def open_access_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=None) as client:
        yield client
        await client.reset_call_tracking()


@pytest_asyncio.fixture
async def sn1_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=identities[IdentityName("sn1")].wallet) as client:
        yield client
        await client.reset_call_tracking()


@pytest_asyncio.fixture
async def sn2_mock_bt_client(mock_bt_client_pool):
    async with mock_bt_client_pool.acquire(wallet=identities[IdentityName("sn2")].wallet) as client:
        yield client
        await client.reset_call_tracking()


@pytest_asyncio.fixture(loop_scope="session")
async def test_app(mock_bt_client_pool: MockBittensorClient, monkeypatch):
    """
    Create a test Litestar app with the mock client pool.
    """
    from contextlib import asynccontextmanager

    from pylon.service.main import create_app

    # Mock the bittensor_client lifespan to just set our mock client
    @asynccontextmanager
    async def mock_lifespan(app):
        app.state.bittensor_client_pool = mock_bt_client_pool
        yield

    # Replace the lifespan in the main module
    monkeypatch.setattr("pylon.service.main.bittensor_client_pool", mock_lifespan)

    app = create_app()
    app.debug = True  # Enable detailed error responses
    return app


@pytest_asyncio.fixture(loop_scope="session")
async def test_client(test_app):
    """
    Create an async test client for the test app.
    """
    async with AsyncTestClient(app=test_app) as client:
        yield client
