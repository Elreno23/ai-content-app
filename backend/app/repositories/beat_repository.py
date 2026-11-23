from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.beat import Beat


class BaseBeatRepository(ABC):
    @abstractmethod
    async def create(self, scene_id: int, number: int, content: str) -> Beat:
        raise NotImplementedError

    @abstractmethod
    async def get(self, beat_id: int) -> Beat | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_scene(self, scene_id: int) -> list[Beat]:
        raise NotImplementedError

    @abstractmethod
    async def next_number(self, scene_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, beat_id: int) -> bool:
        raise NotImplementedError


class BeatRepository(BaseBeatRepository):
    """Persistencia de `Beat`. Flush sin commit: el commit es del servicio."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, scene_id: int, number: int, content: str) -> Beat:
        beat = Beat(scene_id=scene_id, number=number, content=content)
        self.db.add(beat)
        await self.db.flush()
        return beat

    async def get(self, beat_id: int) -> Beat | None:
        return await self.db.get(Beat, beat_id)

    async def list_by_scene(self, scene_id: int) -> list[Beat]:
        result = await self.db.scalars(
            select(Beat).where(Beat.scene_id == scene_id).order_by(Beat.number)
        )
        return list(result)

    async def next_number(self, scene_id: int) -> int:
        current = await self.db.scalar(
            select(func.max(Beat.number)).where(Beat.scene_id == scene_id)
        )
        return (current or 0) + 1

    async def delete(self, beat_id: int) -> bool:
        beat = await self.get(beat_id)
        if beat is None:
            return False
        await self.db.delete(beat)
        await self.db.flush()
        return True
