from pylon._internal.client.abstract import AbstractAsyncPylonClient
from pylon._internal.client.communicators.http import AsyncHttpCommunicator


class AsyncPylonClient(AbstractAsyncPylonClient[AsyncHttpCommunicator]):
    _communicator_cls = AsyncHttpCommunicator
