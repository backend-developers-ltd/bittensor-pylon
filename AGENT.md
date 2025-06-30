# Bittensor Pylon

**Bittensor Pylon** is a high-performance, asynchronous proxy for a Bittensor subnet. It acts as a robust bridge between external applications and the Bittensor blockchain.

This repository contains two main packages:

-   **`pylon_service`**: The core REST API service. This is the main application that runs as a server, connects to the Bittensor network, caches data, and exposes the API endpoints.
-   **`pylon_client`**: A lightweight client library. This package provides a convenient Python interface for interacting with the `pylon_service` API, allowing other applications to easily consume its data.


## Architecture

The application is designed with a clear separation of concerns, organized into the following core components:

-   **Bittensor Client (`pylon_service/bittensor_client.py`):** Manages all interactions with the Bittensor network using the `turbobt` library, including caching metagraphs and handling wallet operations.
-   **API (`pylon_service/api.py`):** The Litestar-based API layer that defines all external endpoints.
-   **Database (`pylon_service/db.py`):** Uses SQLAlchemy and Alembic for async database operations (SQLite) and schema migrations. Primarily stores neuron weights.
-   **Application Logic (`pylon_service/main.py`):** The main entry point. It wires up the application, manages the startup/shutdown lifecycle, and launches background tasks.
-   **Background Tasks (`pylon_service/tasks.py`):** Asynchronous tasks that run periodically.
-   **Data Models (`pylon_service/models.py`):** Pydantic models for data validation and serialization.
-   **Settings (`pylon_service/settings.py`):** Manages application configuration using `pydantic-settings`, loading from a `.env` file.

## API Endpoints

The service exposes several endpoints to interact with the subnet:

-   `/latest_block`: Get the latest processed block number.
-   `/metagraph`: Get the metagraph for the latest block or a specific block.
-   `/block_hash/{block_number}`: Get the block hash for a specific block number.
-   `/epoch`: Get information about the current or a specific epoch.
-   `/hyperparams`: Get cached subnet hyperparameters.
-   `/set_hyperparam`: Set a subnet hyperparameter (subnet owner only).
-   `/update_weight`: Update a hotkey's weight by a delta.
-   `/set_weight`: Set a hotkey's weight.
-   `/raw_weights`: Get raw weights for a given epoch.
-   `/force_commit_weights`: Force a commit of the current DB weights to the subnet.
-   `/get_commitment/{hotkey}`: Get a specific commitment for a hotkey.
-   `/get_commitments`: Get all commitments for the subnet.
-   `/set_commitment`: Set a commitment for the app's wallet.

### Background Tasks (`pylon_service/tasks.py`)

The application runs several background tasks to keep the application state up-to-date:

-   **`fetch_latest_hyperparams_task`**: Periodically fetches and caches the subnet hyperparameters.
-   **`fetch_latest_metagraph_task`**: Periodically fetches and caches the latest metagraph.
-   **`set_weights_periodically_task`**: Periodically checks if it's time to commit weights to the subnet and does so if the conditions are met.

These tasks are managed by the application lifecycle events in `pylon_service/main.py`.


## Dependencies

-   **Web Framework**: Litestar
-   **Bittensor Interaction**: `turbobt`, `bittensor_wallet`
-   **Database**: SQLAlchemy, `aiosqlite`, Alembic
-   **Configuration**: `pydantic-settings`
-   **Caching**: `cachetools`
-   **Containerization**: Docker


## Development

### Setup

Clone the repository and install the dependencies:

```bash
uv pip install -e .[dev]
```

### Running the Application

Locally:

```bash
uvicorn pylon_service.main:app --host 0.0.0.0 --port 8000
```

With Docker:

```bash
PYLON_DOCKER_IMAGE_NAME="bittensor_pylon" PYLON_DB_PATH="data/pylon.db" ./docker-run.sh
```

### Testing

Run the test suite using Nox:

```bash
nox -s test
```

To format the codebase, run:

```bash
nox -s format
```


### Configuration

Create a `.env` file from the example and add your configuration:

```bash
cp .env.example .env
# Edit .env with your wallet and network details
```

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


## turbobt Features

`turbobt` is a Python library providing core functionalities for interacting with the Bittensor blockchain. **bittensor-pylon** utilizes these capabilities, primarily through `app.bittensor_client` and background tasks in `app.tasks`. Key `turbobt` methods and features leveraged include:

- **Blockchain Interaction:**
  - `Bittensor.head.get()`: Fetches the latest block from the blockchain.
  - `Bittensor.block(block_number).get()`: Retrieves a specific block by its number.
  - `Bittensor.subnet(netuid)`: Accesses a specific subnet.
    - `Subnet.list_neurons(block_hash)`: Lists all neurons within a subnet for a given block.
    - `Subnet.get_hyperparameters()`: Fetches the hyperparameters for a subnet.
- **Wallet Integration:** using a `bittensor_wallet.Wallet` instance: `Bittensor(wallet=...)`.
- **Weight Operations:** functionalities for on-chain weight setting and commitments. (Note: `bittensor-pylon` currently manages weights off-chain in its local database for the `/update_weight`, `/set_weight`, `/raw_weights` API endpoints).
- **Admin and System Utilities:** various administrative and system-level utilities, which are generally not directly exposed via `bittensor-pylon`'s public API but can inform internal logic.
- **Asynchronous Design:** All network and blockchain operations within `turbobt` are inherently asynchronous, which is crucial for `bittensor-pylon`'s performance.
