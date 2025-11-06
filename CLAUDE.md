# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bittensor Pylon is a high-performance, asynchronous proxy for a Bittensor subnet. It is a single unified package `pylon` with the following sub-packages:

- **`pylon.service`**: Core REST API service that connects to Bittensor network and exposes API endpoints
- **`pylon._internal.client`**: Lightweight Python client library for interacting with the pylon service API
- **`pylon._internal.common`**: Shared utilities, settings, and request/response models

## Development Commands

### Package Management
- Install dependencies: `uv sync --extra dev`
- Uses `uv` as the package manager (faster than pip).
- Build package: `uv build` (uses hatchling backend with dynamic versioning)

### Running python commands

- Run python command: `uv run python`

### Testing
- Run all tests: `nox -s test`
- Run specific test: `nox -s test -- -k "test_name"`

### Code Quality
- Format and lint: `nox -s format`
- Uses `ruff` for formatting and linting, `pyright` for type checking
- Line length: 120 characters


### Running the Service
- Local development: `uvicorn pylon.service.main:app --host 0.0.0.0 --port 8000`
- Docker: `PYLON_DOCKER_IMAGE_NAME="bittensor_pylon" ./docker-run.sh`

## Architecture

The application follows a clear separation of concerns with these core components:

### Core Components
- **`pylon/service/bittensor/client.py`**: Manages all interactions with the Bittensor network using the `turbobt` library, including wallet operations. Provides `AbstractBittensorClient` base class and `TurboBtClient` implementation
- **`pylon/service/api.py`**: The Litestar-based API layer that defines all external endpoints
- **`pylon/service/main.py`**: The main entry point. It wires up the application, manages the startup/shutdown lifecycle
- **`pylon/service/tasks.py`**: Contains `ApplyWeights` task for applying weights to the subnet on-demand
- **`pylon/service/bittensor/models.py`**: Bittensor-specific models (Block, Neuron, Certificate, etc.)
- **`pylon/_internal/common/settings.py`**: Manages application configuration using `pydantic-settings`, loading from a `.env` file
- **`pylon/_internal/common/requests.py`**: Pydantic request models for API validation
- **`pylon/_internal/common/responses.py`**: Pydantic response models for API serialization
- **`pylon/_internal/client/`**: Client library implementation (`AsyncPylonClient`)

### Key Dependencies
- **Web Framework**: Litestar (not FastAPI)
- **Bittensor**: `turbobt` library for blockchain interaction, `bittensor_wallet` for wallet operations
- **Config**: `pydantic-settings` with `.env` file support
- **HTTP Client**: `httpx` for async HTTP requests
- **Containerization**: Docker

### Background Tasks
- **`ApplyWeights`** (`pylon/service/tasks.py`): Applies weights to the subnet on-demand (triggered by PUT /subnet/weights endpoint)
  - Uses retry logic with exponential backoff (configurable: default 200 attempts, 1-second delay)
  - Handles both commit-reveal and direct weight setting based on subnet hyperparameters

## API Endpoints

All endpoints are prefixed with `/api/v1`. The service currently exposes the following endpoints:

### Weight Management
- **PUT `/api/v1/subnet/weights`**: Set weights for the subnet (triggers background ApplyWeights task)
  - Request body: `{"weights": {"hotkey1": 0.5, "hotkey2": 0.3, ...}}`
  - Automatically handles commit-reveal or direct weight setting based on subnet configuration

### Certificate Operations
- **GET `/api/v1/certificates`**: Get all certificates for the subnet
- **GET `/api/v1/certificates/{hotkey}`**: Get certificate for a specific hotkey
- **GET `/api/v1/certificates/self`**: Get certificate for the app's wallet
- **POST `/api/v1/certificates/self`**: Generate a new certificate keypair
  - Request body: `{"algorithm": 1}` (1 = ED25519, currently the only supported algorithm)


## turbobt Integration

`turbobt` is a Python library providing core functionalities for interacting with the Bittensor blockchain. The application uses it through the `TurboBtClient` implementation in `pylon/service/bittensor/client.py`:

### Key turbobt Features Used
- **Blockchain Interaction**:
  - `Bittensor.head.get()`: Fetches the latest block from the blockchain
  - `Bittensor.block(block).get()`: Retrieves a specific block by its number
  - `Bittensor.subnet(netuid)`: Accesses a specific subnet
    - `Subnet.list_neurons(block_hash)`: Lists all neurons within a subnet for a given block
    - `Subnet.get_hyperparameters()`: Fetches the hyperparameters for a subnet
    - `Subnet.get_certificates()`: Fetches all certificates for a subnet
    - `Subnet.generate_certificate_keypair()`: Generates a new certificate keypair
- **Wallet Integration**: Using a `bittensor_wallet.Wallet` instance: `Bittensor(wallet=...)`
- **Weight Operations**: On-chain weight setting and commit-reveal weights
- **Asynchronous Design**: All network and blockchain operations within `turbobt` are inherently asynchronous

## Configuration

Configuration is managed in `pylon/_internal/common/settings.py` using `pydantic-settings`. Environment variables are loaded from a `.env` file (template at `pylon/service/envs/test_env.template`).

**NOTE**: Settings are currently legacy and need cleanup. Many settings may be unused after the legacy code removal.

### Key Configuration Settings
- **Bittensor network**: `bittensor_netuid`, `bittensor_network` (default: "finney"), `bittensor_archive_network` (default: "archive")
- **Wallet**: `bittensor_wallet_name`, `bittensor_wallet_hotkey_name`, `bittensor_wallet_path`
- **Authentication**: `auth_token` for API authentication
- **Weight settings**: `tempo`, `commit_cycle_length`, `weights_retry_attempts` (default: 200), `weights_retry_delay_seconds` (default: 1)
- **Caching**: `metagraph_cache_ttl`, `metagraph_cache_maxsize`
- **Monitoring**: `sentry_dsn`, `sentry_environment`

## Testing Notes

- Uses `pytest` with `pytest-asyncio` for async test support
- Mock data available in `tests/mock_data.json`
- Both sync (`PylonClient`) and async (`AsyncPylonClient`) clients have built-in mock mode
- Test environment template must be copied to `.env` before running tests

### Service API Testing

The service endpoints are tested using `MockBittensorClient` (`tests/mock_bittensor_client.py`), which provides a mock implementation of `AbstractBittensorClient` for testing without blockchain interactions.

#### MockBittensorClient Features
- **All methods are async**: Including `mock_behavior()` context manager and `reset_call_tracking()`
- **Async Behavior Queue System**: Configure method behaviors using async context manager
  ```python
  async with mock_client.mock_behavior(
      get_latest_block=[Block(number=100, hash=BlockHash("0x123"))],
      _get_certificates=[{hotkey: certificate}],
  ):
      # Test code here
  ```
- **Call Tracking**: All method calls are tracked in `mock_client.calls` dict (using `defaultdict(list)`):
  ```python
  # Check entire call arguments in one assert
  assert mock_client.calls["commit_weights"] == [
      (settings.bittensor_netuid, weights),
  ]
  ```
- **Flexible Behaviors**: Each behavior can be:
  - A value to return directly
  - A callable that receives method arguments
  - An exception instance to raise

#### Test Structure
- **One file per endpoint**: Each endpoint has its own test file (e.g., `test_put_weights_endpoint.py`)
- **Shared fixtures**: Common fixtures in `tests/service/conftest.py`:
  - `mock_bt_client`: Returns a `MockBittensorClient` instance
  - `test_app`: Returns configured Litestar app with mocked client
  - `test_client`: Returns `AsyncTestClient` (async fixture using `@pytest_asyncio.fixture`)
  - `wait_for_background_tasks(task_names)`: Helper in `tests/helpers.py` to wait for async tasks
    - `task_names`: List of task names to wait for, or `None` to wait for all tasks
    - Uses `asyncio.wait()` for native async task synchronization
- **Comprehensive coverage**: Tests cover success cases, error cases, and validation errors

#### Testing Best Practices (REMEMBER FOR ETERNITY)

1. **Response Validation**: ALWAYS check the whole `response.json()` in one assert comparing a complete dict
   ```python
   # ✅ CORRECT
   assert response.json() == {
       "detail": "weights update scheduled",
       "count": 3,
   }

   # ❌ WRONG - multiple asserts
   assert response.json()["detail"] == "weights update scheduled"
   assert response.json()["count"] == 3
   ```

2. **Parametrized Tests**: Use `pytest.mark.parametrize` with `pytest.param` and snake_case IDs
   ```python
   @pytest.mark.parametrize(
       "algorithm",
       [
           pytest.param(0, id="algorithm_zero"),
           pytest.param(2, id="algorithm_two"),
           pytest.param("invalid", id="invalid_type"),
       ],
   )
   ```

3. **URL Hardcoding**: Hard code URLs in tests (don't use constants or variables)
   ```python
   # ✅ CORRECT
   response = await client.get("/api/v1/certificates/self")

   # ❌ WRONG
   response = await client.get(f"{API_PREFIX}/certificates/self")
   ```

4. **Docstring Style**: ALWAYS break line after `"""` even for one-line docstrings
   ```python
   # ✅ CORRECT
   def test_example():
       """
       Test that example works correctly.
       """
       pass

   # ❌ WRONG
   def test_example():
       """Test that example works correctly."""
       pass
   ```

5. **Background Task Synchronization**: Use `wait_for_background_tasks()` helper instead of `asyncio.sleep()`
   ```python
   # ✅ CORRECT - wait for specific tasks
   await wait_for_background_tasks(ApplyWeights.tasks_running)

   # ✅ CORRECT - wait for all background tasks
   await wait_for_background_tasks(None)

   # ❌ WRONG - unreliable timing
   await asyncio.sleep(0.5)
   ```

6. **Mock Behavior Setup**: Account for ALL method calls including those from background tasks
   ```python
   # Background tasks may call get_latest_block multiple times
   async with mock_client.mock_behavior(
       get_latest_block=[
           Block(number=1000, hash=BlockHash("0xabc123")),  # First call
           Block(number=1001, hash=BlockHash("0xabc124")),  # Second call from background task
       ],
   ):
   ```

7. **Call Tracking Validation**: Check entire call arguments in one assert (like response.json())
   ```python
   # ✅ CORRECT - check entire call tuple
   assert mock_client.calls["commit_weights"] == [
       (settings.bittensor_netuid, weights),
   ]

   # ❌ WRONG - separate asserts
   assert len(mock_client.calls["commit_weights"]) == 1
   assert mock_client.calls["commit_weights"][0][0] == settings.bittensor_netuid
   ```

### Client Library Mock Features
- **Hook tracking**: All endpoints have `MagicMock` hooks for verifying calls (e.g., `mock.latest_block.assert_called()`)
- **Response overrides**: Use `override()` method to customize responses per endpoint
- **Error simulation**: Supports 404 responses and custom status codes via overrides

## Development Workflow

1. Create `.env` from template: `cp pylon/service/envs/test_env.template .env`
2. Install dependencies: `uv sync --extra dev`
3. Run tests: `nox -s test`
4. Format code: `nox -s format`
5. Run service: `uvicorn pylon.service.main:app --reload --host 127.0.0.1 --port 8000`

### Release Process
1. Update version in `pylon/__init__.py`
2. Push git tag: `git tag v0.0.4 && git push`

## Important Implementation Details

- **No database**: Database layer has been removed (legacy code cleanup). All operations are direct blockchain interactions
- **Weight management**: Weights are submitted directly to the blockchain via the `ApplyWeights` background task
- **Client library**: Only `AsyncPylonClient` is provided (sync client removed)
- **Bittensor client abstraction**: `AbstractBittensorClient` base class with `TurboBtClient` implementation for production
- **Testing**: `MockBittensorClient` provides testing implementation without blockchain interactions
- **Async-first**: All operations are asynchronous using `asyncio`
- **Architecture pattern**: Communicator pattern used in client library (HTTP, Mock communicators)
- Use nox for running tests
