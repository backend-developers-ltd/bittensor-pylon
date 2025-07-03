# Bittensor Pylon

**Bittensor Pylon** is a high-performance, asynchronous proxy for a Bittensor subnet. It acts as a robust bridge between external applications and the Bittensor blockchain.

This repository contains two main packages:

-   **`pylon_service`**: The core REST API service. This is the main application that runs as a server, connects to the Bittensor network, caches data, and exposes the API endpoints.
-   **`pylon_client`**: A lightweight client library. This package provides a convenient Python interface for interacting with the `pylon_service` API, allowing other applications to easily consume its data.



## Development

### Setup and Configuration

Clone the repository and install the dependencies:
```bash
git clone https://github.com/your-repo/bittensor-pylon.git
cd bittensor-pylon
uv pip install -e .[dev]
```

Configure the environment by creating a `.env` file based on the provided template (`pylon_service/envs/test_env.template`)


### Running the Pylon Service

locally:
```bash
uvicorn pylon_service.main:app --host 0.0.0.0 --port 8000
```

or with Docker:
```bash
PYLON_DOCKER_IMAGE_NAME="bittensor_pylon" PYLON_DB_PATH="data/pylon.db" ./docker-run.sh
```

### Using the Pylon Client


Below is a brief example of how to use the client:

```python
import asyncio
from pylon_client.client import PylonClient
from pylon_client.docker_manager import PylonDockerManager

async def main():
    async with PylonClient(port=port) as client:
        # start the Pylon service docker container manually or use the PylonDockerManager
        async with PylonDockerManager(client=client):
            latest_block = await client.get_latest_block()
            print(f"The latest block is: {latest_block}")

if __name__ == "__main__":
    asyncio.run(main())
```

For testing, you can run the `PylonClient` in a mock mode by providing a path to a JSON file containing mock data. This allows you to test your application without a live `pylon_service` instance.
The client's mock mode provides hooks for asserting that endpoints were called and allows you to override default mock responses for specific tests.

```python
import asyncio
from pylon_client.client import PylonClient

# Create a mock_data.json file with your desired responses:
# {
#   "metagraph": { "block": 12345, "neurons": [] },
#   "hyperparams": { "rho": 10, "kappa": 32767 }
# }

async def main():
    # Initialize the client with the path to your mock data
    client = PylonClient(mock_data_path="path/to/mock_data.json")

    async with client:
        # The client will return data from your mock file
        latest_block = await client.get_latest_block()
        print(f"Mocked latest block: {latest_block}")
        # You can assert that the mock was called
        client.mock.get_latest_block.assert_called_once()

        # You can also override a specific response for a test
        client.override("get_latest_block", {"block": 99999})
        overridden_block = await client.get_latest_block()
        print(f"Overridden latest block: {overridden_block}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Testing

This project uses `nox` for managing development tasks.
*   **Format/Lint code:** `nox -s format`
*   **Run tests:** `nox -s test`
*   **Run a specific test:** `nox -s test -- -k "test_name"`


### Database Migrations

Before running the application for the first time, apply the database migrations.

If you've changed the database models in `pylon_service/db.py`, generate a new migration script:
```bash
nox -s generate-migration -- "Your migration message"
```

Then, apply the migrations to the database:
```bash
alembic upgrade head
```


---

For more information on the architecture and API endpoints please see [AGENT.md](AGENT.md).

