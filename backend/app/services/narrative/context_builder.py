"""ContextBuilder v1 (H3.2): ensambla el contexto del LLM desde el plano estructural.

Sin snapshot, sin resumen rodante (H3.3/P10): solo lectura — biblia de la serie,
loglines de capítulos anteriores y logline del capítulo objetivo. Solo lectura:
nunca muta la base de datos ni llama al LLM.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter
from app.models.season import Season
from app.models.series import Series


class ContextBuilder:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build_chapter_context(self, chapter_id: int) -> dict:
        chapter = await self.db.get(Chapter, chapter_id)
        if chapter is None:
            raise ValueError(f"Capítulo {chapter_id} no encontrado")
        season = await self.db.get(Season, chapter.season_id)
        series = await self.db.get(Series, season.series_id)
        previous_rows = await self.db.scalars(
            select(Chapter)
            .where(
                Chapter.season_id == season.id,
                Chapter.number < chapter.number,
            )
            .order_by(Chapter.number)
        )
        previous = [
            {
                "number": ch.number,
                "logline": ch.logline,
                "narrative_status": ch.narrative_status,
            }
            for ch in previous_rows
        ]
        return {
            "series_name": series.name,
            "bible": series.bible,
            "max_chapters_per_season": series.max_chapters_per_season,
            "season_number": season.number,
            "chapter_number": chapter.number,
            "chapter_logline": chapter.logline,
            "previous_chapters": previous,
        }
