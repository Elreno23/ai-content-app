from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.season import Season


class BaseSeasonRepository(ABC):
    @abstractmethod
    async def create(
        self, series_id: int, number: int, title: str | None = None
    ) -> Season:
        raise NotImplementedError

    @abstractmethod
    async def get(self, season_id: int) -> Season | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_series(self, series_id: int) -> list[Season]:
        raise NotImplementedError

    @abstractmethod
    async def next_number(self, series_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, season_id: int) -> bool:
        raise NotImplementedError


class SeasonRepository(BaseSeasonRepository):
    """Persistencia de `Season`. Flush sin commit: el commit es del servicio."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, series_id: int, number: int, title: str | None = None
    ) -> Season:
        season = Season(series_id=series_id, number=number, title=title)
        self.db.add(season)
        await self.db.flush()
        return season

    async def get(self, season_id: int) -> Season | None:
        return await self.db.get(Season, season_id)

    async def list_by_series(self, series_id: int) -> list[Season]:
        result = await self.db.scalars(
            select(Season)
            .where(Season.series_id == series_id)
            .order_by(Season.number)
        )
        return list(result)

    async def next_number(self, series_id: int) -> int:
        current = await self.db.scalar(
            select(func.max(Season.number)).where(Season.series_id == series_id)
        )
        return (current or 0) + 1

    async def delete(self, season_id: int) -> bool:
        season = await self.get(season_id)
        if season is None:
            return False
        await self.db.delete(season)
        await self.db.flush()
        return True
