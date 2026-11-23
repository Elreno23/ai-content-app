"""ChapterService (H3.2): desarrollo narrativo de un capítulo.

Decisiones aprobadas: una sola llamada LLM por capítulo; aprobación humana a
nivel de capítulo completo; sin revision/regeneración parcial (aplazadas).
Atomicidad: una sesión, un commit, rollback ante cualquier fallo — los
repositorios solo hacen flush.
"""

import logging
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NarrativeStateError
from app.repositories.beat_repository import BeatRepository
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.scene_repository import SceneRepository
from app.schemas.parsers.chapter_parser import (
    MAX_BEATS_PER_SCENE,
    MAX_SCENES,
    MIN_BEATS_PER_SCENE,
    MIN_SCENES,
    ChapterStructure,
)
from app.services.ai.base_ai import BaseAIProvider
from app.services.narrative.context_builder import ContextBuilder

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.models.chapter import Chapter


class ChapterService:
    def __init__(self, db: AsyncSession, llm_provider: BaseAIProvider) -> None:
        self.db = db
        self.provider = llm_provider
        self.chapter_repo = ChapterRepository(db)
        self.scene_repo = SceneRepository(db)
        self.beat_repo = BeatRepository(db)
        self.context_builder = ContextBuilder(db)

    async def develop_chapter(self, chapter_id: int) -> "Chapter":
        chapter = await self.chapter_repo.get(chapter_id)
        if chapter is None:
            raise NarrativeStateError(f"El capítulo {chapter_id} no existe.")
        if chapter.narrative_status != "planned":
            raise NarrativeStateError(
                f"El capítulo {chapter_id} no está en estado 'planned' "
                f"(estado actual: '{chapter.narrative_status}')."
            )
        context = await self.context_builder.build_chapter_context(chapter_id)
        prompt = self._build_development_prompt(context)
        structure = await self.provider.generate_chapter_structure(prompt)
        try:
            await self._persist_structure(chapter, structure)
            chapter.narrative_status = "narrative_complete"
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return chapter

    async def approve_narrative(self, chapter_id: int) -> "Chapter":
        chapter = await self.chapter_repo.get(chapter_id)
        if chapter is None:
            raise NarrativeStateError(f"El capítulo {chapter_id} no existe.")
        if chapter.narrative_status != "narrative_complete":
            raise NarrativeStateError(
                f"Solo se puede aprobar un capítulo en estado 'narrative_complete' "
                f"(estado actual: '{chapter.narrative_status}')."
            )
        try:
            chapter.narrative_status = "narrative_approved"
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return chapter

    async def _persist_structure(
        self, chapter, structure: ChapterStructure
    ) -> None:
        for scene_data in structure.scenes:
            scene = await self.scene_repo.create(
                chapter.id,
                scene_data.number,
                title=scene_data.title,
                summary=scene_data.summary,
            )
            for beat_data in scene_data.beats:
                await self.beat_repo.create(
                    scene.id, beat_data.number, beat_data.content
                )

    def _build_development_prompt(self, context: dict) -> str:
        bible = context.get("bible") or {}
        bible_text = ", ".join(
            f"{k}: {v}" for k, v in bible.items() if v is not None
        ) or "Sin biblia definida"
        logline = context.get("chapter_logline") or "Sin logline definida"
        previous = context.get("previous_chapters") or []
        previous_text = (
            "\n".join(
                f"[Capítulo {ch['number']}] {ch['logline']}"
                for ch in previous
                if ch.get("logline")
            )
            or "Este es el primer capítulo de la temporada."
        )
        return f"""Eres el guionista técnico de una serie narrativa. Tu única tarea es desarrollar
el capítulo {context.get('chapter_number')} de la temporada {context.get('season_number')} de la serie
"{context.get('series_name')}".

BIBLIA DE LA SERIE:
{bible_text}

CAPÍTULOS ANTERIORES DE LA TEMPORADA:
{previous_text}

LOGLINE DE ESTE CAPÍTULO (lo que debe ocurrir):
{logline}

REGLAS DE NARRATIVA:
- Escribe en tiempo presente y describe acciones físicas inmediatas y concretas.
- Cada escena sigue exactamente donde terminó la anterior (continuidad estricta).
- Prohibido el resumen literario: cada beat es una acción o momento congelado.
- La última escena cierra con un gancho.

REGLAS DE ESTRUCTURA (OBLIGATORIAS):
- Entre {MIN_SCENES} y {MAX_SCENES} escenas, numeradas desde 1 de forma consecutiva.
- Cada escena entre {MIN_BEATS_PER_SCENE} y {MAX_BEATS_PER_SCENE} beats, numerados desde 1 de forma consecutiva.
- Prohibido generar menos de {MIN_BEATS_PER_SCENE} beats por escena.

REGLAS DE FORMATO:
- Devuelve SOLO JSON, sin texto fuera del JSON, sin campos adicionales.
- Estructura exacta:
{{
  "chapter": {{
    "title": "string o null",
    "summary": "string",
    "scenes": [
      {{
        "number": 1,
        "title": "string o null",
        "summary": "string",
        "beats": [
          {{ "number": 1, "content": "string" }}
        ]
      }}
    ]
  }}
}}

Ahora desarrolla el capítulo siguiendo TODAS las reglas."""
