from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter


class BaseChapterRepository(ABC):
    @abstractmethod
    async def create(
        self,
        season_id: int,
        number: int,
        title: str | None = None,
        logline: str | None = None,
    ) -> Chapter:
        raise NotImplementedError

    @abstractmethod
    async def get(self, chapter_id: int) -> Chapter | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_season(self, season_id: int) -> list[Chapter]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_status(self, status: str) -> list[Chapter]:
        raise NotImplementedError

    @abstractmethod
    async def next_number(self, season_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    async def update_status(self, chapter_id: int, status: str) -> Chapter | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, chapter_id: int) -> bool:
        raise NotImplementedError


class ChapterRepository(BaseChapterRepository):
    """Persistencia de `Chapter`. Flush sin commit: el commit es del servicio."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        season_id: int,
        number: int,
        title: str | None = None,
        logline: str | None = None,
    ) -> Chapter:
        chapter = Chapter(
            season_id=season_id,
            number=number,
            title=title,
            logline=logline,
        )
        self.db.add(chapter)
        await self.db.flush()
        return chapter

    async def get(self, chapter_id: int) -> Chapter | None:
        return await self.db.get(Chapter, chapter_id)

    async def list_by_season(self, season_id: int) -> list[Chapter]:
        result = await self.db.scalars(
            select(Chapter)
            .where(Chapter.season_id == season_id)
            .order_by(Chapter.number)
        )
        return list(result)

    async def list_by_status(self, status: str) -> list[Chapter]:
        result = await self.db.scalars(
            select(Chapter).where(Chapter.status == status).order_by(Chapter.id)
        )
        return list(result)

    async def next_number(self, season_id: int) -> int:
        current = await self.db.scalar(
            select(func.max(Chapter.number)).where(Chapter.season_id == season_id)
        )
        return (current or 0) + 1

    async def update_status(self, chapter_id: int, status: str) -> Chapter | None:
        chapter = await self.get(chapter_id)
        if chapter is None:
            return None
        chapter.status = status
        await self.db.flush()
        return chapter

    async def delete(self, chapter_id: int) -> bool:
        chapter = await self.get(chapter_id)
        if chapter is None:
            return False
        await self.db.delete(chapter)
        await self.db.flush()
        return True
