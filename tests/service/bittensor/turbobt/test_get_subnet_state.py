import pytest

from pylon._internal.common.currency import CurrencyRao, Token
from pylon._internal.common.models import Block, SubnetState
from pylon._internal.common.types import (
    AlphaStakeRao,
    BlockHash,
    BlockNumber,
    Coldkey,
    Consensus,
    Dividends,
    EmissionRao,
    Hotkey,
    Incentive,
    NetUid,
    PruningScore,
    Rank,
    SubnetActive,
    TaoStakeRao,
    Timestamp,
    TotalStakeRao,
    Trust,
    ValidatorPermit,
)


@pytest.fixture
def test_block():
    return Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))


@pytest.fixture
def subnet_spec(subnet_spec):
    subnet_spec.get_state.return_value = {
        "netuid": 1,
        "hotkeys": ["hotkey1", "hotkey2"],
        "coldkeys": ["coldkey1", "coldkey2"],
        "active": [True, False],
        "validator_permit": [True, False],
        "pruning_score": [100, 200],
        "last_update": [1000, 2000],
        "emission": [10_000_000_000, 20_000_000_000],
        "dividends": [500_000_000, 300_000_000],
        "incentives": [800_000_000, 600_000_000],
        "consensus": [900_000_000, 700_000_000],
        "trust": [850_000_000, 750_000_000],
        "rank": [950_000_000, 650_000_000],
        "block_at_registration": [100, 200],
        "alpha_stake": [100_000_000_000, 200_000_000_000],
        "tao_stake": [50_000_000_000, 75_000_000_000],
        "total_stake": [150_000_000_000, 275_000_000_000],
        "emission_history": [
            [5_000_000_000, 6_000_000_000],
            [7_000_000_000, 8_000_000_000],
        ],
    }
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_subnet_state(turbobt_client, subnet_spec, test_block):
    result = await turbobt_client.get_subnet_state(netuid=NetUid(1), block=test_block)
    assert result == SubnetState(
        netuid=NetUid(1),
        hotkeys=[Hotkey("hotkey1"), Hotkey("hotkey2")],
        coldkeys=[Coldkey("coldkey1"), Coldkey("coldkey2")],
        active=[SubnetActive(True), SubnetActive(False)],
        validator_permit=[ValidatorPermit(True), ValidatorPermit(False)],
        pruning_score=[PruningScore(100), PruningScore(200)],
        last_update=[Timestamp(1000), Timestamp(2000)],
        emission=[
            EmissionRao(CurrencyRao[Token.ALPHA](10_000_000_000)),
            EmissionRao(CurrencyRao[Token.ALPHA](20_000_000_000)),
        ],
        dividends=[Dividends(500_000_000), Dividends(300_000_000)],
        incentives=[Incentive(800_000_000), Incentive(600_000_000)],
        consensus=[Consensus(900_000_000), Consensus(700_000_000)],
        trust=[Trust(850_000_000), Trust(750_000_000)],
        rank=[Rank(950_000_000), Rank(650_000_000)],
        block_at_registration=[BlockNumber(100), BlockNumber(200)],
        alpha_stake=[
            AlphaStakeRao(CurrencyRao[Token.ALPHA](100_000_000_000)),
            AlphaStakeRao(CurrencyRao[Token.ALPHA](200_000_000_000)),
        ],
        tao_stake=[
            TaoStakeRao(CurrencyRao[Token.TAO](50_000_000_000)),
            TaoStakeRao(CurrencyRao[Token.TAO](75_000_000_000)),
        ],
        total_stake=[
            TotalStakeRao(CurrencyRao[Token.ALPHA](150_000_000_000)),
            TotalStakeRao(CurrencyRao[Token.ALPHA](275_000_000_000)),
        ],
        emission_history=[
            [
                EmissionRao(CurrencyRao[Token.ALPHA](5_000_000_000)),
                EmissionRao(CurrencyRao[Token.ALPHA](6_000_000_000)),
            ],
            [
                EmissionRao(CurrencyRao[Token.ALPHA](7_000_000_000)),
                EmissionRao(CurrencyRao[Token.ALPHA](8_000_000_000)),
            ],
        ],
    )
    subnet_spec.get_state.assert_called_once_with(test_block.hash)
