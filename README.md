# Bittensor Pylon

**Bittensor Pylon** is a high-performance, asynchronous proxy for Bittensor subnets. It provides fast, cached access to Bittensor blockchain data through a REST API, making it easy for applications to interact with the Bittensor network without direct blockchain calls.

## What's Included

- **REST API Service**: High-performance server that connects to Bittensor and exposes REST endpoints
- **Python Client Library**: Simple async client for consuming the API with built-in retry logic and mock support

Full API documentation is available at `/schema/swagger` when the service is running.


## Running the REST API on Docker

### Configuration

Create a `.env` file with your Bittensor settings by copying the template:

```bash
# Copy the template and edit it
cp pylon/service/envs/test_env.template .env
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
cp pylon/service/envs/docker-compose.yaml.example docker-compose.yaml
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

### Prometheus Metrics Endpoint

The service exposes Prometheus metrics at the `/metrics` endpoint for monitoring and observability. This endpoint is
protected with Bearer token authentication.

**Configuration:**

Set the `PYLON_METRICS_TOKEN` environment variable in your `.env` file:

```bash
PYLON_METRICS_TOKEN=your-secure-metrics-token
```

**Important:** If `PYLON_METRICS_TOKEN` is empty or not set, the `/metrics` endpoint will return `403 Forbidden` to
prevent unauthorized access.

**Accessing the metrics:**

```bash
curl http://localhost:8000/metrics -H "Authorization: Bearer your-secure-metrics-token"
```

**Available metrics:**

The endpoint provides the following Prometheus metrics organized by category:

**HTTP API Metrics:**
- `pylon_requests_total` - Total number of HTTP requests
- `pylon_request_duration_seconds` - HTTP request duration in seconds (histogram)
- `pylon_requests_in_progress` - Number of HTTP requests currently being processed (gauge)

All HTTP metrics include labels: `method`, `path`, `status_code`, `app_name`.

**Bittensor Blockchain Metrics:**
- `pylon_bittensor_operation_duration_seconds` - Duration of blockchain operations (histogram)
  - Labels: `operation`, `status` (success/error), `client_type` (main/archive), `netuid`, `hotkey`
  - Buckets: 0.1s, 0.5s, 1s, 2s, 5s, 10s, 30s, 60s, 120s
- `pylon_bittensor_errors_total` - Total number of errors in blockchain operations (counter)
  - Labels: `operation`, `exception`, `client_type`, `netuid`, `hotkey`
- `pylon_bittensor_fallback_total` - Archive client fallback events (counter)
  - Labels: `reason`, `operation`, `hotkey`

**ApplyWeights Job Metrics:**
- `pylon_apply_weights_job_duration_seconds` - Duration of entire ApplyWeights job execution (histogram)
  - Buckets: 1s, 5s, 10s, 30s, 60s, 120s, 300s, 600s, 1200s
- `pylon_apply_weights_attempt_duration_seconds` - Duration of individual weight application attempts (histogram)
  - Buckets: 0.1s, 0.5s, 1s, 2s, 5s, 10s, 30s, 60s, 120s

**Python Runtime Metrics:**

Standard Python process metrics are also exposed: memory usage, CPU time, garbage collection stats, and file descriptors.

**Note:** All counter and histogram metrics automatically include `*_created` gauge metrics showing the timestamp when each label combination was first seen. You can disable these by setting `PROMETHEUS_DISABLE_CREATED_SERIES=True` in your environment to reduce metrics output.

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

from pylon.v1 import (
    AsyncPylonClient, 
    AsyncPylonClientConfig, 
    BlockNumber, 
    GetNeuronsRequest,
    GetLatestNeuronsRequest,
    Hotkey, 
    SetWeightsRequest, 
    Weight
)


async def main():
    config = AsyncPylonClientConfig(address="http://127.0.0.1:8000")
    async with AsyncPylonClient(config) as client:
        # Get the current metagraph
        metagraph = await client.request(GetLatestNeuronsRequest())
        print(f"Block: {metagraph.block.number}, Neurons: {len(metagraph.neurons)}")

        # Get metagraph for a specific block
        metagraph = await client.request(GetNeuronsRequest(block_number=BlockNumber(1000)))

        # Set weights
        # Wrapping values with Hotkey and Weight is recommended but not necessary if type checker isn't used.
        await client.request(SetWeightsRequest(weights={Hotkey("h1"): Weight(0.1)}))


if __name__ == "__main__":
    asyncio.run(main())
```

If you need to manage the Pylon service programmatically, you can use the `PylonDockerManager`. 
It's a context manager that starts the Pylon service and stops it when the `async with` block is exited. Only suitable for ad-hoc use cases like scripts, short-lived tasks or testing.

```python
from pylon.v1 import AsyncPylonClient, AsyncPylonClientConfig, SetWeightsRequest, PylonDockerManager, Hotkey, Weight

async def main():
    async with PylonDockerManager(port=8000):
        config = AsyncPylonClientConfig(address="http://127.0.0.1:8000")
        async with AsyncPylonClient(config) as client:
            await client.request(SetWeightsRequest(weights={Hotkey("h1"): Weight(0.1)}))
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


### Input data validation

The client performs the input data validation when constructing the request object:

```python
SetWeightsRequest(weights=0.2)  # ValidationError will happen here - weights argument expects a dictionary
```

The error is always of pydantic.ValidationError type. 
See the [pydantic documentation](https://docs.pydantic.dev/latest/errors/errors/) for the error reference.

**Warning:** passing a proper request to a client does prevent the PylonResponseException caused by the improper data,
however it may still be raised for other reasons (improper app state, server error etc.)

#### Bypassing validation

Validation on a client side prevents from sending a malformed data to the server. However, this way validation is
performed twice (on a client side and on a server side). If you want to skip the client side validation, construct
the request using `model_construct` class method:

```python
SetWeightsRequest.model_construct(weights=0.2)
```

No error will be raised until the request is made and data errors are detected by the server. In case the server
receives malformed request, the client will raise `PylonResponseException`:

```python
# Request is made, raises PylonResponseException.
await client.request(SetWeightsRequest.model_construct(weights=0.2))
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
