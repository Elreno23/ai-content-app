from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.series import Series


class BaseSeriesRepository(ABC):
    @abstractmethod
    async def create(
        self,
        name: str,
        bible: dict | None = None,
        max_chapters_per_season: int | None = None,
    ) -> Series:
        raise NotImplementedError

    @abstractmethod
    async def get(self, series_id: int) -> Series | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[Series]:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        series_id: int,
        *,
        name: str | None = None,
        bible: dict | None = None,
        max_chapters_per_season: int | None = None,
    ) -> Series | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, series_id: int) -> bool:
        raise NotImplementedError


class SeriesRepository(BaseSeriesRepository):
    """Persistencia de `Series`. Flush sin commit: el commit es del servicio."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        name: str,
        bible: dict | None = None,
        max_chapters_per_season: int | None = None,
    ) -> Series:
        series = Series(
            name=name,
            bible=bible,
            max_chapters_per_season=max_chapters_per_season,
        )
        self.db.add(series)
        await self.db.flush()
        return series

    async def get(self, series_id: int) -> Series | None:
        return await self.db.get(Series, series_id)

    async def list_all(self) -> list[Series]:
        result = await self.db.scalars(select(Series).order_by(Series.id))
        return list(result)

    async def update(
        self,
        series_id: int,
        *,
        name: str | None = None,
        bible: dict | None = None,
        max_chapters_per_season: int | None = None,
    ) -> Series | None:
        series = await self.get(series_id)
        if series is None:
            return None
        if name is not None:
            series.name = name
        if bible is not None:
            series.bible = bible
        if max_chapters_per_season is not None:
            series.max_chapters_per_season = max_chapters_per_season
        await self.db.flush()
        return series

    async def delete(self, series_id: int) -> bool:
        series = await self.get(series_id)
        if series is None:
            return False
        await self.db.delete(series)
        await self.db.flush()
        return True
