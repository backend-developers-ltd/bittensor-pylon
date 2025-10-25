"""
Shared fixtures for service endpoint tests.
"""

import pytest
import pytest_asyncio
from litestar.testing import AsyncTestClient

from tests.mock_bittensor_client import MockBittensorClient


@pytest.fixture
def mock_bt_client():
    """
    Create a mock Bittensor client.
    """
    return MockBittensorClient()


@pytest.fixture
def test_app(mock_bt_client: MockBittensorClient, monkeypatch):
    """
    Create a test Litestar app with the mock client.
    """
    from contextlib import asynccontextmanager

    from pylon.service.main import create_app

    # Mock the bittensor_client lifespan to just set our mock client
    @asynccontextmanager
    async def mock_lifespan(app):
        app.state.bittensor_client = mock_bt_client
        yield

    # Replace the lifespan in the main module
    monkeypatch.setattr("pylon.service.main.bittensor_client", mock_lifespan)

    app = create_app()
    app.debug = True  # Enable detailed error responses
    return app


@pytest_asyncio.fixture
async def test_client(test_app):
    """
    Create an async test client for the test app.
    """
    async with AsyncTestClient(app=test_app) as client:
        yield client
