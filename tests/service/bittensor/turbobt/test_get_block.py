import pytest
from turbobt.block import Block as TurboBtBlock

from pylon._internal.common.models import Block
from pylon._internal.common.types import BlockHash, BlockNumber


@pytest.mark.asyncio
async def test_turbobt_client_get_block(turbobt_client, block_spec):
    block_spec.get.return_value = TurboBtBlock("hash", 202, client=turbobt_client._raw_client)
    result = await turbobt_client.get_block(BlockNumber(202))
    assert result == Block(hash=BlockHash("hash"), number=BlockNumber(202))
