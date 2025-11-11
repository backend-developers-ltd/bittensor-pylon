from ipaddress import IPv4Address

import pytest
from httpx import ConnectTimeout, Response, codes
from pydantic import ValidationError

from pylon._internal.common.currency import Currency, Token
from pylon._internal.common.exceptions import PylonRequestException, PylonResponseException
from pylon._internal.common.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    Neuron,
    Stakes,
)
from pylon._internal.common.requests import GetNeuronsRequest
from pylon._internal.common.responses import GetNeuronsResponse
from pylon._internal.common.types import (
    AlphaStake,
    BlockHash,
    BlockNumber,
    Coldkey,
    Consensus,
    Dividends,
    Emission,
    Hotkey,
    Incentive,
    NeuronActive,
    NeuronUid,
    Port,
    PruningScore,
    Rank,
    Stake,
    TaoStake,
    Timestamp,
    TotalStake,
    Trust,
    ValidatorPermit,
    ValidatorTrust,
)


@pytest.fixture
def neurons_json():
    return {
        "block": {"number": 1000, "hash": "0xabc123"},
        "neurons": {
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty": {
                "uid": 0,
                "coldkey": "5C4hrfjw9DjXZTzV3MwzrrAr9P1MJhSrvWGWqi1eSuyUpnhM",
                "hotkey": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
                "active": True,
                "axon_info": {"ip": "192.168.1.1", "port": 8091, "protocol": 4},
                "stake": 100.5,
                "rank": 0.95,
                "emission": 10.5,
                "incentive": 0.85,
                "consensus": 0.9,
                "trust": 0.88,
                "validator_trust": 0.92,
                "dividends": 5.5,
                "last_update": 500,
                "validator_permit": True,
                "pruning_score": 1000,
                "stakes": {"alpha": 75.0, "tao": 45.0, "total": 83.1},
            },
            "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY": {
                "uid": 1,
                "coldkey": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
                "hotkey": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
                "active": True,
                "axon_info": {"ip": "192.168.1.2", "port": 8092, "protocol": 0},
                "stake": 200.75,
                "rank": 0.88,
                "emission": 12.3,
                "incentive": 0.78,
                "consensus": 0.85,
                "trust": 0.82,
                "validator_trust": 0.87,
                "dividends": 6.2,
                "last_update": 501,
                "validator_permit": False,
                "pruning_score": 950,
                "stakes": {"alpha": 150.0, "tao": 90.0, "total": 166.2},
            },
        },
    }


@pytest.fixture
def expected_neurons_response(neurons_json):
    block_data = neurons_json["block"]
    neurons_data = neurons_json["neurons"]

    neurons = {}
    for hotkey, neuron_data in neurons_data.items():
        neurons[Hotkey(hotkey)] = Neuron(
            uid=NeuronUid(neuron_data["uid"]),
            coldkey=Coldkey(neuron_data["coldkey"]),
            hotkey=Hotkey(neuron_data["hotkey"]),
            active=NeuronActive(neuron_data["active"]),
            axon_info=AxonInfo(
                ip=IPv4Address(neuron_data["axon_info"]["ip"]),
                port=Port(neuron_data["axon_info"]["port"]),
                protocol=AxonProtocol(neuron_data["axon_info"]["protocol"]),
            ),
            stake=Stake(neuron_data["stake"]),
            rank=Rank(neuron_data["rank"]),
            emission=Emission(Currency[Token.ALPHA](neuron_data["emission"])),
            incentive=Incentive(neuron_data["incentive"]),
            consensus=Consensus(neuron_data["consensus"]),
            trust=Trust(neuron_data["trust"]),
            validator_trust=ValidatorTrust(neuron_data["validator_trust"]),
            dividends=Dividends(neuron_data["dividends"]),
            last_update=Timestamp(neuron_data["last_update"]),
            validator_permit=ValidatorPermit(neuron_data["validator_permit"]),
            pruning_score=PruningScore(neuron_data["pruning_score"]),
            stakes=Stakes(
                alpha=AlphaStake(Currency[Token.ALPHA](neuron_data["stakes"]["alpha"])),
                tao=TaoStake(Currency[Token.TAO](neuron_data["stakes"]["tao"])),
                total=TotalStake(Currency[Token.ALPHA](neuron_data["stakes"]["total"])),
            ),
        )

    return GetNeuronsResponse(
        block=Block(number=BlockNumber(block_data["number"]), hash=BlockHash(block_data["hash"])),
        neurons=neurons,
    )


@pytest.mark.asyncio
async def test_async_client_get_neurons_success(async_client, service_mock, neurons_json, expected_neurons_response):
    route = service_mock.get("/api/v1/neurons/1000")
    route.mock(return_value=Response(status_code=codes.OK, json=neurons_json))

    async with async_client:
        response = await async_client.request(GetNeuronsRequest(block_number=BlockNumber(1000)))

    assert response == expected_neurons_response


@pytest.mark.asyncio
async def test_async_client_get_neurons_empty_neurons(async_client, service_mock):
    neurons_json = {
        "block": {"number": 100, "hash": "0x123abc"},
        "neurons": {},
    }
    route = service_mock.get("/api/v1/neurons/100")
    route.mock(return_value=Response(status_code=codes.OK, json=neurons_json))

    async with async_client:
        response = await async_client.request(GetNeuronsRequest(block_number=BlockNumber(100)))

    assert response == GetNeuronsResponse(
        block=Block(number=BlockNumber(100), hash=BlockHash("0x123abc")),
        neurons={},
    )


@pytest.mark.asyncio
async def test_async_client_get_neurons_retries_success(async_client, service_mock, neurons_json):
    service_mock.get("/api/v1/neurons/1000").mock(
        side_effect=[
            ConnectTimeout("Connection timed out"),
            ConnectTimeout("Connection timed out"),
            Response(status_code=codes.OK, json=neurons_json),
        ]
    )

    async with async_client:
        response = await async_client.request(GetNeuronsRequest(block_number=BlockNumber(1000)))

    assert response.block.number == 1000
    assert len(response.neurons) == 2


@pytest.mark.asyncio
async def test_async_client_get_neurons_request_error(async_client, service_mock):
    assert async_client.config.retry.stop.max_attempt_number <= 3
    service_mock.get("/api/v1/neurons/1000").mock(
        side_effect=ConnectTimeout("Connection timed out"),
    )

    async with async_client:
        with pytest.raises(PylonRequestException, match="An error occurred while making a request to Pylon API."):
            await async_client.request(GetNeuronsRequest(block_number=BlockNumber(1000)))


@pytest.mark.asyncio
async def test_async_client_get_neurons_response_error(async_client, service_mock):
    service_mock.get("/api/v1/neurons/1000").mock(return_value=Response(status_code=codes.INTERNAL_SERVER_ERROR))

    async with async_client:
        with pytest.raises(PylonResponseException, match="Invalid response from Pylon API."):
            await async_client.request(GetNeuronsRequest(block_number=BlockNumber(1000)))


@pytest.mark.parametrize(
    "invalid_block_number,expected_errors",
    [
        pytest.param(
            "not_a_number",
            [
                {
                    "type": "int_parsing",
                    "loc": ("block_number",),
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                }
            ],
            id="string_value",
        ),
        pytest.param(
            123.456,
            [
                {
                    "type": "int_from_float",
                    "loc": ("block_number",),
                    "msg": "Input should be a valid integer, got a number with a fractional part",
                }
            ],
            id="float_value",
        ),
        pytest.param(
            [123],
            [{"type": "int_type", "loc": ("block_number",), "msg": "Input should be a valid integer"}],
            id="list_value",
        ),
        pytest.param(
            {"block": 123},
            [{"type": "int_type", "loc": ("block_number",), "msg": "Input should be a valid integer"}],
            id="dict_value",
        ),
    ],
)
def test_get_neurons_request_validation_error(invalid_block_number, expected_errors):
    """
    Test that GetNeuronsRequest validates block_number type correctly.
    """
    with pytest.raises(ValidationError) as exc_info:
        GetNeuronsRequest(block_number=invalid_block_number)  # type: ignore

    errors = exc_info.value.errors(include_url=False, include_context=False, include_input=False)
    assert errors == expected_errors
