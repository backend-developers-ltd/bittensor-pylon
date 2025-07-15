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

The client automatically manages the Docker container for you:

```python
import asyncio
from pylon_client.client import PylonClient
from pylon_client.docker_manager import PylonDockerManager

async def main():
    async with PylonClient(port=8000) as client:
        # (Optional) start/stop the service container
        async with PylonDockerManager(client=client):
            # Get latest block information
            latest_block = await client.get_latest_block()
            print(f"Latest block: {latest_block}")
            
            # Get metagraph data
            metagraph = await client.get_metagraph()
            print(f"Metagraph: {metagraph}")
            
            # Get hyperparameters
            hyperparams = await client.get_hyperparams()
            print(f"Hyperparams: {hyperparams}")

if __name__ == "__main__":
    asyncio.run(main())
```

Or If you have a service already running elsewhere:

```python
async def main():
    async with PylonClient(base_url="http://your-server.com", port=8000) as client:
        latest_block = await client.get_latest_block()
        ...

```

### Mock Mode for Testing

For testing without a live service:

```python
import asyncio
from pylon_client.client import PylonClient

async def main():
    # Use mock data from JSON file
    client = PylonClient(mock_data_path="tests/mock_data.json")
    
    async with client:
        # Returns mock data
        latest_block = await client.get_latest_block()
        print(f"Mocked latest block: {latest_block}")
        
        # Verify the mock was called
        client.mock.get_latest_block.assert_called_once()
        
        # Override responses for specific tests
        client.override("get_latest_block", {"block": 99999})
        overridden_block = await client.get_latest_block()
        print(f"Overridden block: {overridden_block}")

if __name__ == "__main__":
    asyncio.run(main())
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
nox -s generate-migration -- "Your migration message"
```

Apply database migrations:
```bash
alembic upgrade head
```

