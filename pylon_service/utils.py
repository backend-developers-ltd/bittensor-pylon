from pylon_common.models import Epoch
from pylon_common.settings import settings


def get_epoch_containing_block(
    block: int, netuid: int = settings.bittensor_netuid, tempo: int = settings.tempo
) -> Epoch:
    """
    Reimplementing the logic from subtensor's Rust function:
        pub fn blocks_until_next_epoch(netuid: u16, tempo: u16, block: u64) -> u64
    See https://github.com/opentensor/subtensor.
    See also: https://github.com/opentensor/bittensor/pull/2168/commits/9e8745447394669c03d9445373920f251630b6b8

    The beginning of an epoch is the first block when values like "dividends" are different
    (before an epoch they are constant for a full tempo).
    """
    assert tempo > 0

    interval = tempo + 1
    next_epoch = block + tempo - (block + netuid + 1) % interval

    if next_epoch == block:
        prev_epoch = next_epoch
        next_epoch = prev_epoch + interval
    else:
        prev_epoch = next_epoch - interval

    return Epoch(start=prev_epoch, end=next_epoch)


class CommitWindow:
    """
    722     epoch commit window            1443
    |_____________|_________________|________|
    |   OFFSET    |  COMMIT WINDOW  | BUFFER |

    """

    def __init__(
        self,
        current_block: int,
    ):
        self.current_block = current_block
        self.interval = settings.tempo
        self.commit_start_offset = settings.commit_window_start_offset
        self.commit_end_buffer = settings.commit_window_end_buffer

    @property
    def start(self):
        """
        https://github.com/opentensor/subtensor/blob/af585b9b8a17d27508431257052da502055477b7/pallets/subtensor/src/subnets/weights.rs#L488
        """
        return self.current_block - self.current_block % self.interval

    @property
    def stop(self):
        return self.start + self.interval

    @property
    def commit_start(self):
        return self.start + self.commit_start_offset

    @property
    def commit_stop(self):
        return self.stop - self.commit_end_buffer

    @property
    def commit_window(self):
        return range(self.commit_start, self.commit_stop)
