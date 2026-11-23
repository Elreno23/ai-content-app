from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scene import Scene


class BaseSceneRepository(ABC):
    @abstractmethod
    async def create(
        self,
        chapter_id: int,
        number: int,
        title: str | None = None,
        summary: str | None = None,
    ) -> Scene:
        raise NotImplementedError

    @abstractmethod
    async def get(self, scene_id: int) -> Scene | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_chapter(self, chapter_id: int) -> list[Scene]:
        raise NotImplementedError

    @abstractmethod
    async def next_number(self, chapter_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, scene_id: int) -> bool:
        raise NotImplementedError


class SceneRepository(BaseSceneRepository):
    """Persistencia de `Scene`. Flush sin commit: el commit es del servicio."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        chapter_id: int,
        number: int,
        title: str | None = None,
        summary: str | None = None,
    ) -> Scene:
        scene = Scene(
            chapter_id=chapter_id,
            number=number,
            title=title,
            summary=summary,
        )
        self.db.add(scene)
        await self.db.flush()
        return scene

    async def get(self, scene_id: int) -> Scene | None:
        return await self.db.get(Scene, scene_id)

    async def list_by_chapter(self, chapter_id: int) -> list[Scene]:
        result = await self.db.scalars(
            select(Scene)
            .where(Scene.chapter_id == chapter_id)
            .order_by(Scene.number)
        )
        return list(result)

    async def next_number(self, chapter_id: int) -> int:
        current = await self.db.scalar(
            select(func.max(Scene.number)).where(Scene.chapter_id == chapter_id)
        )
        return (current or 0) + 1

    async def delete(self, scene_id: int) -> bool:
        scene = await self.get(scene_id)
        if scene is None:
            return False
        await self.db.delete(scene)
        await self.db.flush()
        return True
