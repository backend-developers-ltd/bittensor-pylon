# Bittensor Pylon

**Bittensor Pylon** is a high-performance, asynchronous proxy for Bittensor subnets. It provides fast, cached access to Bittensor blockchain data through a REST API, making it easy for applications to interact with the Bittensor network without direct blockchain calls.

## What's Included

- **REST API Service** (`pylon_service`): High-performance server that connects to Bittensor, caches subnet data, and exposes REST endpoints
- **Python Client Library** (`pylon_client`): Simple async client for consuming the API with built-in retry logic and mock support

Full API documentation is available at `/schema/swagger` when the service is running.


## Quick Start

### Configuration

Create a `.env` file with your Bittensor settings:

```bash
# Copy the template and edit it
cp pylon_service/envs/test_env.template .env
```

Optionally add Sentry DSN for error tracking in production:
```bash
SENTRY_DSN=your_sentry_dsn_here
SENTRY_ENVIRONMENT=production
```

#### Weight Committing Window

Pylon commits weights within specific time windows every X epochs:
```
    0            180               350      360
    |_____________|_________________|________|
    |   OFFSET    |  COMMIT WINDOW  | BUFFER |
```

- **`COMMIT_WINDOW_START_OFFSET`** (default: 180): Blocks after epoch start before commits begin
- **`COMMIT_WINDOW_END_BUFFER`** (default: 10): Blocks before epoch end when commits stop
- **`COMMIT_CYCLE_LENGTH`** (default: 3): Number of epochs between weight commits

Example: With defaults, the commit window is open from block 180 to block 350 of each epoch, and weights are committed every 3 epochs.

### Run the service

Using official docker image:

```bash
docker pull backenddevelopersltd/bittensor-pylon:v1-latest
docker run --rm --env-file .env -v "$(pwd)/data:/app/db/" -p 8000:8000 backenddevelopersltd/bittensor-pylon:v1-latest
```

or building and running locally:
```bash
./docker-run.sh
```

Test the endpoints at `http://localhost:8000/schema/swagger`



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
