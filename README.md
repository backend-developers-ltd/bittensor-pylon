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

The client can connect to a running Pylon service. For production or long-lived services, you should run the Pylon service directly using Docker as described in the "Run the service" section.
Use the PylonClient to connect with the running service:

```python
from pylon_client import PylonClient

def main():
    client = PylonClient(base_url="http://your-server.com:port")

    block = client.get_latest_block()
    print(f"Latest block: {block}")

    metagraph = client.get_metagraph()
    print(f"Metagraph: {metagraph}")

    hyperparams = client.get_hyperparams()
    print(f"Hyperparams: {hyperparams}")

if __name__ == "__main__":
    main()
```

or using the AsyncPylonClient:

```python
import asyncio
from pylon_client.client import AsyncPylonClient
from pylon_client.docker_manager import PylonDockerManager

async def main():
    async with AsyncPylonClient(base_url="http://your-server.com:port") as client:
        block = await client.get_latest_block()
        print(f"Latest block: {block}")
        ...

if __name__ == "__main__":
    asyncio.run(main())
```

If you need to manage the Pylon service programmatically you can use the `PylonDockerManager`. 
It's a context manager that starts the Pylon service and stops it when the `async with` block is exited. Only suitable for ad-hoc use cases like scripts, short-lived tasks or testing.

```python
async def main():
    async with AsyncPylonClient(base_url="http://your-server.com:port") as client:
        async with PylonDockerManager(port=port) as client:
            block = await client.get_latest_block()
            print(f"Latest block: {block}")
            ...

```

### Mock Mode for Testing

For testing without a live service:

```python
from pylon_client.client import PylonClient

def main():
    # Use mock data from JSON file
    client = PylonClient(mock_data_path="tests/mock_data.json")

    # Returns mock data - client methods return specific types
    block = client.get_latest_block()
    print(f"Mocked latest block: {block}")

    metagraph = client.get_metagraph()
    print(f"Mocked metagraph block: {metagraph.block}")

    # Verify the mock was called
    client.mock.latest_block.assert_called_once()

    # Override responses for specific tests
    client.override("get_latest_block/", 99999)
    block = client.get_latest_block()
    assert block == 99999

if __name__ == "__main__":
    main()
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
