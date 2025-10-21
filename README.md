# Bittensor Pylon

**Bittensor Pylon** is a high-performance, asynchronous proxy for Bittensor subnets. It provides fast, cached access to Bittensor blockchain data through a REST API, making it easy for applications to interact with the Bittensor network without direct blockchain calls.

## What's Included

- **REST API Service** (`pylon_service`): High-performance server that connects to Bittensor, caches subnet data, and exposes REST endpoints
- **Python Client Library** (`pylon_client`): Simple async client for consuming the API with built-in retry logic and mock support

Full API documentation is available at `/schema/swagger` when the service is running.


## Running the REST API on Docker

### Configuration

Create a `.env` file with your Bittensor settings by copying the template:

```bash
# Copy the template and edit it
cp pylon_service/envs/test_env.template .env
```

Edit the example values in `.env` file to the desired ones. The meaning of each setting is described in the file.

### Run the service

Run the Docker container passing the `.env` file created in a previous step. Remember to use the appropriate image tag
and mount your wallet to the directory set in configuration.

```bash
docker pull backenddevelopersltd/bittensor-pylon:git-169a0e490aa92b7d0ca6392d65eb0d322c5b700c
docker run -d --env-file .env -v "/path/to/my/wallet/:/root/.bittensor/wallets" -p 8000:8000 backenddevelopersltd/bittensor-pylon:git-169a0e490aa92b7d0ca6392d65eb0d322c5b700c
```

This will run the Pylon on the local machine's port 8000.

Alternatively, you can use docker-compose to run the container. To archive this, copy the example `docker-compose.yaml` 
file to the same location as `.env` file:

```bash
# Make sure to remove .example from the file name!
cp pylon_service/envs/docker-compose.yaml.example docker-compose.yaml
```

Edit the file according to your needs (especially wallets volume) and run:

```bash
docker compose up -d
```

## Using the REST API

All endpoints are listed at `http://localhost:8000/schema/swagger`.

Every request must be authenticated by providing the `Authorization` header with the Bearer token. Request will be 
authenticated properly, if the token sent in request matches the token set by the `AUTH_TOKEN` setting.

Example of the proper request using `curl`:

```bash
curl -X PUT http://localhost:8000/api/v1/subnet/weights --data '{"weights": {"hk1": 0.8, "hk2": 0.5}}' -H "Authorization: Bearer abc"
```

## Using the Python Client

Install the client library:
```bash
pip install git+https://github.com/backend-developers-ltd/bittensor-pylon.git
```

### Basic Usage

The client can connect to a running Pylon service. For production or long-lived services, 
you should run the Pylon service directly using Docker as described in the "Running the REST API on Docker" section. 
Use the Pylon client to connect with the running service:

```python
import asyncio

from pylon.v1 import AsyncPylonClient, AsyncPylonClientConfig, SetWeightsRequest

async def main():
    config = AsyncPylonClientConfig(address="http://127.0.0.1:8000")
    async with AsyncPylonClient(config) as client:
        await client.request(SetWeightsRequest(weights={"h1": 0.1}))

if __name__ == "__main__":
    asyncio.run(main())
```

If you need to manage the Pylon service programmatically, you can use the `PylonDockerManager`. 
It's a context manager that starts the Pylon service and stops it when the `async with` block is exited. Only suitable for ad-hoc use cases like scripts, short-lived tasks or testing.

```python
from pylon.v1 import AsyncPylonClient, AsyncPylonClientConfig, SetWeightsRequest, PylonDockerManager

async def main():
    async with PylonDockerManager(port=8000):
        config = AsyncPylonClientConfig(address="http://127.0.0.1:8000")
        async with AsyncPylonClient(config) as client:
            await client.request(SetWeightsRequest(weights={"h1": 0.1}))
                ...
```

### Retries

In case of an unsuccessful request, Pylon client will automatically retry it. By default, request will fail after 3rd.
failed attempt.

Retrying behavior can be tweaked by passing a `retry` argument to the client config. It accepts an instance of
[tenacity.AsyncRetrying](https://tenacity.readthedocs.io/en/latest/api.html#tenacity.AsyncRetrying); please refer to
[tenacity documentation](https://tenacity.readthedocs.io/en/latest/index.html).

**Example:**

This example shows how to configure the client to retry up to 5 times, waiting between 0.1 and 0.3 seconds after every 
attempt.

```python
from pylon.v1 import AsyncPylonClient, AsyncPylonClientConfig, PylonRequestException

from tenacity import AsyncRetrying, stop_after_attempt, retry_if_exception_type, wait_random

async def main():
    config = AsyncPylonClientConfig(
        address="http://127.0.0.1:8000",
        retry=AsyncRetrying(
            wait=wait_random(min=0.1, max=0.3),
            stop=stop_after_attempt(5),
            retry=retry_if_exception_type(PylonRequestException),
        )
    )
    async with AsyncPylonClient(config) as client:
        ...
```

To avoid manual exception handling, we recommend using `pylon.v1.DEFAULT_RETRIES` object as following:


```python
from pylon.v1 import AsyncPylonClient, AsyncPylonClientConfig, DEFAULT_RETRIES

from tenacity import stop_after_attempt, wait_random

async def main():
    config = AsyncPylonClientConfig(
        address="http://127.0.0.1:8000",
        retry=DEFAULT_RETRIES.copy(
            wait=wait_random(min=0.1, max=0.3),
            stop=stop_after_attempt(5),
        )
    )
    async with AsyncPylonClient(config) as client:
        ...
```


## Development

Run tests:
```bash
nox -s test                    # Run all tests
nox -s test -- -k "test_name"  # Run specific test
```

Format and lint code:
```bash
nox -s format                  # Format code with ruff and run type checking
```

Generate new migrations after model changes:
```bash
uv run alembic revision --autogenerate -m "Your migration message"
```

Apply database migrations:
```bash
alembic upgrade head
```
