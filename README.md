# Bittensor Pylon

**Bittensor Pylon** is a high-performance, asynchronous proxy for Bittensor subnets. It provides fast, cached access to Bittensor blockchain data through a REST API, making it easy for applications to interact with the Bittensor network without direct blockchain calls.

## What's Included

- **REST API Service** (`pylon_service`): High-performance server that connects to Bittensor, caches subnet data, and exposes REST endpoints
- **Python Client Library** (`pylon_client`): Simple async client for consuming the API with built-in retry logic and mock support

## Quick Start

### Using Docker (Recommended)

1. **Pull and run the service:**
   ```bash
   docker pull backenddevelopersltd/bittensor-pylon:v1-latest
   docker run --rm \
     --env-file .env \
     -v "$(pwd)/data:/app/db/" \
     -p 8000:8000 \
     backenddevelopersltd/bittensor-pylon:v1-latest
   ```

2. **Access the API:**
   - API endpoints: `http://localhost:8000`
   - API documentation: `http://localhost:8000/schema/swagger`

### Configuration

Create a `.env` file with your Bittensor settings:

```bash
# Copy the template
cp pylon_service/envs/test_env.template .env

# Edit with your settings
BITTENSOR_NETUID=12
BITTENSOR_NETWORK=finney
BITTENSOR_WALLET_NAME=your-wallet-name
BITTENSOR_WALLET_HOTKEY_NAME=your-hotkey-name
BITTENSOR_WALLET_PATH=~/.bittensor/wallets/your-wallet-name/
AM_I_A_VALIDATOR=True
```

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

## API Endpoints

Key endpoints available:

- `GET /latest_block` - Get the latest processed block number
- `GET /metagraph` - Get metagraph data for latest or specific block
- `GET /hyperparams` - Get cached subnet hyperparameters
- `GET /epoch` - Get current epoch information
- `POST /set_weight` - Set validator weights (validators only)
- `POST /update_weight` - Update validator weights by delta (validators only)
- `POST /force_commit_weights` - Force commit weights to subnet (validators only)

Full API documentation is available at `/schema/swagger` when the service is running.

## Development

### Local Development Setup

1. **Clone and install:**
   ```bash
   git clone https://github.com/backend-developers-ltd/bittensor-pylon.git
   cd bittensor-pylon
   uv pip install -e .[dev]
   ```

2. **Configure environment:**
   ```bash
   cp pylon_service/envs/test_env.template .env
   # Edit .env with your Bittensor settings
   ```

3. **Set up database:**
   ```bash
   alembic upgrade head
   ```

4. **Run locally:**
   ```bash
   uvicorn pylon_service.main:app --host 0.0.0.0 --port 8000
   ```

### Development with Docker

Build and run locally:
```bash
PYLON_DOCKER_IMAGE_NAME="bittensor_pylon" PYLON_DB_DIR="data/" ./docker-run.sh
```

### Testing and Code Quality

Run tests:
```bash
nox -s test                    # Run all tests
nox -s test -- -k "test_name"  # Run specific test
```

Format and lint code:
```bash
nox -s format                  # Format code with ruff and run type checking
```

### Database Migrations

Generate new migrations after model changes:
```bash
nox -s generate-migration -- "Your migration message"
```

Apply migrations:
```bash
alembic upgrade head
```

