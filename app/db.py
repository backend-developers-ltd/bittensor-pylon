import asyncio
import datetime
import logging

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, sessionmaker

from app.models import Neuron
from app.settings import settings

DB_PATH = settings.bittensor_pylon_db

engine = create_async_engine(DB_PATH, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

logger = logging.getLogger(__name__)


class Weight(Base):
    __tablename__ = "weights"
    id = Column(Integer, primary_key=True, index=True)
    hotkey = Column(String, index=True, nullable=False)
    epoch = Column(Integer, index=True, nullable=False)
    weight = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


# For easy import in main
async def init_db():
    try:
        alembic_cfg = AlembicConfig("alembic.ini")
        await asyncio.to_thread(alembic_command.upgrade, alembic_cfg, "head")
    except Exception as e:
        logger.error(f"Error applying database migrations: {e}")
        raise


async def _get_weight(session: AsyncSession, hotkey: str, epoch: int) -> Weight | None:
    weights = await session.execute(select(Weight).where((Weight.hotkey == hotkey) & (Weight.epoch == epoch)))
    return weights.scalars().first()


async def set_weight(hotkey: str, weight: float, epoch: int) -> None:
    async with SessionLocal() as session:
        existing_weight = await _get_weight(session, hotkey, epoch)
        if existing_weight:
            existing_weight.weight = weight
        else:
            new_weight = Weight(hotkey=hotkey, weight=weight, epoch=epoch)
            session.add(new_weight)
        await session.commit()


async def update_weight(hotkey: str, delta: float, epoch: int) -> float:
    """
    Add delta to the weight for the given epoch. If no record exists, create one with delta as the weight.
    """
    w = None
    async with SessionLocal() as session:
        existing_weight = await _get_weight(session, hotkey, epoch)
        if existing_weight:
            existing_weight.weight += delta
            w = existing_weight.weight
        else:
            new_weight = Weight(hotkey=hotkey, weight=delta, epoch=epoch)
            session.add(new_weight)
            w = delta
        await session.commit()
    return w


async def get_raw_weights(epoch: int) -> dict[str, float]:
    """
    Fetch all miner weights for a given epoch.
    Returns a dict: {hotkey: weight}
    """
    async with SessionLocal() as session:
        result = await session.execute(select(Weight).where(Weight.epoch == epoch))
        weights = result.scalars().all()
        return {m.hotkey: m.weight for m in weights}


async def get_neurons_weights(neurons: list[Neuron], epoch: int) -> dict[int, float]:
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

        weights_by_hotkey = dict(result.all())
        return {neuron.uid: weights_by_hotkey.get(neuron.hotkey, 0.0) for neuron in neurons}
