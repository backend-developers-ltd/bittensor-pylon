import pytest
import respx

from pylon._internal.client.asynchronous import AsyncPylonClient
from pylon._internal.client.config import AsyncPylonClientConfig


@pytest.fixture
def test_url():
    return "http://testserver:8080"


@pytest.fixture
def async_client(test_url):
    return AsyncPylonClient(AsyncPylonClientConfig(address=test_url))


@pytest.fixture
def api_mock(test_url):
    with respx.mock(base_url=test_url) as respx_mock:
        yield respx_mock
