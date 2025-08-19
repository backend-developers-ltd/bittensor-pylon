# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bittensor Pylon is a high-performance, asynchronous proxy for a Bittensor subnet. It consists of two main packages:

- **`pylon_service`**: Core REST API service that connects to Bittensor network, caches data, and exposes API endpoints
- **`pylon_client`**: Lightweight Python client library for interacting with the pylon_service API

## Development Commands

### Package Management
- Install dependencies: `uv sync --extra dev`
- Uses `uv` as the package manager (faster than pip)
- Build package: `uv build` (uses hatchling backend with dynamic versioning)

### Testing
- Run all tests: `nox -s test`
- Run specific test: `nox -s test -- -k "test_name"`

### Code Quality
- Format and lint: `nox -s format`
- Uses `ruff` for formatting and linting, `pyright` for type checking
- Line length: 120 characters

### Database Operations
- Generate migration: `uv run alembic revision --autogenerate -m "Your migration message"`
- Apply migrations: `alembic upgrade head`
- Database uses SQLite with async support via `aiosqlite`

### Running the Service
- Local development: `uvicorn pylon_service.main:app --host 0.0.0.0 --port 8000`
- Docker: `PYLON_DOCKER_IMAGE_NAME="bittensor_pylon" PYLON_DB_DIR="data/" ./docker-run.sh`

## Architecture

The application follows a clear separation of concerns with these core components:

### Core Components
- **`pylon_service/bittensor_client.py`**: Manages all interactions with the Bittensor network using the `turbobt` library, including caching metagraphs and handling wallet operations
- **`pylon_service/api.py`**: The Litestar-based API layer that defines all external endpoints with validator/subnet owner access controls
- **`pylon_service/db.py`**: Uses SQLAlchemy and Alembic for async database operations (SQLite) and schema migrations. Primarily stores neuron weights
- **`pylon_service/main.py`**: The main entry point. It wires up the application, manages the startup/shutdown lifecycle, and launches background tasks
- **`pylon_service/tasks.py`**: Asynchronous tasks that run periodically
- **`pylon_service/models.py`**: Pydantic models for data validation and serialization
- **`pylon_service/settings.py`**: Manages application configuration using `pydantic-settings`, loading from a `.env` file

### Key Dependencies
- **Web Framework**: Litestar (not FastAPI)
- **Bittensor**: `turbobt` library for blockchain interaction, `bittensor_wallet` for wallet operations
- **Database**: SQLAlchemy + aiosqlite + Alembic for migrations
- **Config**: `pydantic-settings` with `.env` file support
- **Caching**: `cachetools` for in-memory caching
- **Containerization**: Docker

### Background Tasks (`pylon_service/tasks.py`)
The application runs several background tasks to keep the application state up-to-date:
- **`fetch_latest_hyperparams_task`**: Periodically fetches and caches the subnet hyperparameters
- **`fetch_latest_metagraph_task`**: Periodically fetches and caches the latest metagraph
- **`set_weights_periodically_task`**: Periodically checks if it's time to commit weights to the subnet and does so if the conditions are met

These tasks are managed by the application lifecycle events in `pylon_service/main.py`.

## API Endpoints

The service exposes several endpoints to interact with the subnet:

### Core Bittensor Data
- `/latest_block`: Get the latest processed block number
- `/latest_metagraph`: Get the metagraph for the latest block
- `/metagraph/{block}`: Get the metagraph for a specific block number
- `/block_hash/{block}`: Get the block hash for a specific block number
- `/epoch`: Get information about the current or a specific epoch
- `/hyperparams`: Get cached subnet hyperparameters

### Weight Management (Off-chain in DB)
- `/update_weight`: Update a hotkey's weight by a delta
- `/set_weight`: Set a hotkey's weight
- `/set_weights`: Set multiple hotkeys' weights at once (batch operation)
- `/latest_weights`: Get weights for the current epoch
- `/weights/{block}`: Get weights for the epoch containing the specified block
- `/force_commit_weights`: Force a commit of the current DB weights to the subnet

### Commitment Operations
- `/commitment/{hotkey}`: Get a specific commitment for a hotkey
- `/commitments`: Get all commitments for the subnet
- `/set_commitment`: Set a commitment for the app's wallet

### Subnet Configuration
- `/set_hyperparam`: Set a subnet hyperparameter (subnet owner only)


## turbobt Integration

`turbobt` is a Python library providing core functionalities for interacting with the Bittensor blockchain. The application leverages these capabilities primarily through `app.bittensor_client` and background tasks:

### Key turbobt Features Used
- **Blockchain Interaction**:
  - `Bittensor.head.get()`: Fetches the latest block from the blockchain
  - `Bittensor.block(block).get()`: Retrieves a specific block by its number
  - `Bittensor.subnet(netuid)`: Accesses a specific subnet
    - `Subnet.list_neurons(block_hash)`: Lists all neurons within a subnet for a given block
    - `Subnet.get_hyperparameters()`: Fetches the hyperparameters for a subnet
- **Wallet Integration**: Using a `bittensor_wallet.Wallet` instance: `Bittensor(wallet=...)`
- **Weight Operations**: Functionalities for on-chain weight setting and commitments
- **Asynchronous Design**: All network and blockchain operations within `turbobt` are inherently asynchronous, crucial for performance

Note: bittensor-pylon currently manages weights off-chain in its local database for the `/update_weight`, `/set_weight`, `/set_weights`, `/latest_weights`, `/weights/{block}` API endpoints for performance reasons.

## Configuration

Environment variables configured via `.env` file (template at `pylon_service/envs/test_env.template`):
- Bittensor network settings (netuid, network, wallet info)
- Database configuration
- Task intervals and timing settings
- Validator/subnet owner permissions

## Testing Notes

- Uses `pytest` with `pytest-asyncio` for async test support
- Mock data available in `tests/mock_data.json`
- Both sync (`PylonClient`) and async (`AsyncPylonClient`) clients have built-in mock mode
- Test environment template must be copied to `.env` before running tests

### Mock Client Features
- **Hook tracking**: All endpoints have `MagicMock` hooks for verifying calls (e.g., `mock.latest_block.assert_called()`)
- **Response overrides**: Use `override()` method to customize responses per endpoint
- **Error simulation**: Supports 404 responses and custom status codes via overrides

## Development Workflow

1. Create `.env` from template: `cp pylon_service/envs/test_env.template .env`
2. Install dependencies: `uv sync --extra dev`
3. Run database migrations: `alembic upgrade head`
4. Run tests: `nox -s test`
5. Format code: `nox -s format`
6. Run service: `uvicorn pylon_service.main:app --reload --host 127.0.0.1 --port 8000`

### Release Process
1. Update version in `pylon_client/__init__.py`
2. Push git tag: `git tag v0.0.4 && git push`

## Important Implementation Details

- All database operations are async using SQLAlchemy with aiosqlite
- Weights are managed off-chain in local database for performance
- Background tasks use asyncio with proper shutdown handling
- Caching uses TTL-based in-memory cache for metagraph data
- Access control via decorators: `@validator_only`, `@subnet_owner_only`
- Uses `turbobt` for efficient Bittensor blockchain interactions
- Client library provides both sync (`PylonClient`) and async (`AsyncPylonClient`) implementations
