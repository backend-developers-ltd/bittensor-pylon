import asyncio
import datetime
import logging
import subprocess
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from pylon_common.models import Hotkey, Neuron
from pylon_common.settings import settings

engine = create_async_engine(settings.pylon_db_uri, echo=False, future=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


logger = logging.getLogger(__name__)


class Weight(Base):
    __tablename__ = "weights"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hotkey: Mapped[str] = mapped_column(String, index=True, nullable=False)
    epoch: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[Any] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )


# For easy import in main
async def init_db():
    try:
        logger.info("Applying database migrations...")
        process = await asyncio.create_subprocess_exec(
            "alembic", "upgrade", "head", stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Alembic upgrade failed: {stderr.decode()}")

        logger.info("Database migrations applied successfully.")
    except Exception as e:
        logger.error(f"Error applying database migrations: {e}", exc_info=True)
        raise


async def get_weight(session: AsyncSession, hotkey: Hotkey, epoch: int) -> Weight | None:
    weights = await session.execute(select(Weight).where((Weight.hotkey == hotkey) & (Weight.epoch == epoch)))
    return weights.scalars().first()


async def set_weight(hotkey: Hotkey, weight: float, epoch: int) -> None:
    async with SessionLocal() as session:
        existing_weight = await get_weight(session, hotkey, epoch)
        if existing_weight:
            existing_weight.weight = weight
        else:
            new_weight = Weight(hotkey=hotkey, weight=weight, epoch=epoch)
            session.add(new_weight)
        await session.commit()


async def update_weight(hotkey: Hotkey, delta: float, epoch: int) -> float:
    """
    Add delta to the weight for the given epoch. If no record exists, create one with delta as the weight.
    """
    w = None
    async with SessionLocal() as session:
        existing_weight = await get_weight(session, hotkey, epoch)
        if existing_weight:
            existing_weight.weight += delta
            w = existing_weight.weight
        else:
            new_weight = Weight(hotkey=hotkey, weight=delta, epoch=epoch)
            session.add(new_weight)
            w = delta
        await session.commit()
    return w


async def get_hotkey_weights_dict(epoch: int) -> dict[Hotkey, float]:
    """
    Fetch all miner weights for a given epoch.
    Returns a dict: {hotkey: weight}
    """
    async with SessionLocal() as session:
        result = await session.execute(select(Weight).where(Weight.epoch == epoch))
        weights = result.scalars().all()
        return {m.hotkey: m.weight for m in weights}


async def get_uid_weights_dict(neurons: list[Neuron], epoch: int) -> dict[int, float]:
    """
    Returns a dict {uid: weight} for the given list of Neurons for the specified epoch.
    """
    if not neurons:
        return {}

    async with SessionLocal() as session:
        # Get all weights for the neuron hotkeys in the given epoch
        hotkeys = [neuron.hotkey for neuron in neurons]
        result = await session.execute(
            select(Weight.hotkey, Weight.weight).where((Weight.hotkey.in_(hotkeys)) & (Weight.epoch == epoch))
        )

        weights_by_hotkey = {row.hotkey: row.weight for row in result.all()}
        return {neuron.uid: weights_by_hotkey.get(neuron.hotkey, 0.0) for neuron in neurons}


async def set_weights_batch(weights: list[tuple[Hotkey, float]], epoch: int) -> None:
    """
    Set multiple weights in a single transaction.
    Args:
        weights: List of (hotkey, weight) tuples
        epoch: The epoch to set weights for
    """
    async with SessionLocal() as session:
        # Fetch all existing weights for this epoch
        hotkeys = [hotkey for hotkey, _ in weights]
        result = await session.execute(select(Weight).where((Weight.hotkey.in_(hotkeys)) & (Weight.epoch == epoch)))
        existing_weights = {w.hotkey: w for w in result.scalars().all()}

        # Update existing or create new weights
        for hotkey, weight in weights:
            if hotkey in existing_weights:
                existing_weights[hotkey].weight = weight
            else:
                new_weight = Weight(hotkey=hotkey, weight=weight, epoch=epoch)
                session.add(new_weight)

        await session.commit()
