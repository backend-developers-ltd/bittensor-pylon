from pydantic import BaseModel, ConfigDict
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from pylon._internal.common.exceptions import PylonRequestException


class PylonAsyncClientConfig(BaseModel):
    """
    Configuration for the asynchronous Pylon clients.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    address: str
    retry: AsyncRetrying = AsyncRetrying(
        wait=wait_exponential_jitter(initial=0.1, jitter=0.2),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(PylonRequestException),
    )
