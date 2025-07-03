import asyncio
import logging
import os
from types import TracebackType

import docker
from docker.models.containers import Container

from pylon_client.client import PylonClient
from pylon_service.settings import settings

logger = logging.getLogger(__name__)


class PylonDockerManager:
    """An asynchronous context manager for starting and stopping the Pylon service in a Docker container."""

    def __init__(self, client: PylonClient):
        self.client = client
        self.container: Container | None = None
        self._docker_client = None

    @property
    def docker_client(self):
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    async def __aenter__(self):
        """Starts the pylon service in a docker container and waits for it to be ready."""
        logger.info("Starting pylon service container...")
        try:
            self.container = await asyncio.to_thread(
                self.docker_client.containers.run,
                settings.pylon_docker_image_name,
                detach=True,
                ports={"8000/tcp": self.client.port},
                volumes={os.path.abspath(settings.pylon_db_path): {"bind": "/app/pylon.db", "mode": "rw"}},
                environment=settings.model_dump(),
            )
            await self._wait_for_service()
            logger.info(f"Pylon container {self.container.short_id} started.")
        except Exception:
            logger.error("Failed to start Pylon service container.")
            if self.container:
                await self.stop_service()
            raise

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stops the pylon service container."""
        await self.stop_service()

    async def stop_service(self):
        if self.container:
            logger.info(f"Stopping pylon container {self.container.short_id}...")
            try:
                await asyncio.to_thread(self.container.stop)
                await asyncio.to_thread(self.container.remove)
                logger.info("Pylon container stopped and removed.")
            except Exception as e:
                logger.error(f"Failed to stop or remove container: {e}")
            finally:
                self.container = None

    async def _wait_for_service(self) -> None:
        await asyncio.sleep(1)
        while not await self._check_service():
            await asyncio.sleep(1)

    async def _check_service(self) -> bool:
        try:
            await self.client.get_latest_block()
        except Exception as e:
            logger.error(f"Pylon service check failed: {e}")
            return False
        return True
