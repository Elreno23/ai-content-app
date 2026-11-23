import asyncio

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import LLMResponseError, NarrativeStateError
from app.repositories.beat_repository import BeatRepository
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.scene_repository import SceneRepository
from app.repositories.season_repository import SeasonRepository
from app.repositories.series_repository import SeriesRepository
from app.schemas.parsers.chapter_parser import (
    MAX_BEATS_PER_SCENE,
    MAX_SCENES,
    MIN_BEATS_PER_SCENE,
    MIN_SCENES,
    ChapterOutput,
    ChapterStructure,
)
from app.services.ai.base_ai import BaseAIProvider
from app.services.narrative.chapter_service import ChapterService
from app.services.narrative.context_builder import ContextBuilder

from tests.test_h3_1_structure import (  # noqa: F401
    fresh,
    make_session_maker,
    run,
    test_db_url,
)


def valid_chapter_payload() -> dict:
    scenes = []
    titles = ["El Regreso", "La Oferta", "La Escalada", "El Cierre con gancho"]
    summaries = [
        "Andres llega a la casa con una maleta.",
        "Andres despliega el contrato sobre la mesa.",
        "La discusion escala y los nervios se rompen.",
        "Juan decide y el capitulo cierra con una revelacion.",
    ]
    for i, (title, summary) in enumerate(zip(titles, summaries), start=1):
        scenes.append(
            {
                "number": i,
                "title": title,
                "summary": summary,
                "beats": [
                    {
                        "number": 1,
                        "content": f"Andres realiza la accion concreta numero {i} de la escena {i}.",
                    },
                    {
                        "number": 2,
                        "content": f"Juan reacciona con una accion fisica concreta en la escena {i}.",
                    },
                ],
            }
        )
    return {
        "chapter": {
            "title": "La Oferta",
            "summary": "Andres llega con una propuesta que Juan no puede rechazar.",
            "scenes": scenes,
        }
    }


def structure_from_payload() -> ChapterStructure:
    return ChapterOutput.model_validate(valid_chapter_payload()).chapter


class FakeProvider(BaseAIProvider):
    def __init__(self, structure=None, error=None):
        self.structure = structure
        self.error = error
        self.last_prompt = None

    async def generate_chapter_structure(self, prompt):
        self.last_prompt = prompt
        if self.error is not None:
            raise self.error
        return self.structure


# ---------- Parser / validador CHAPTER_SCHEMA ----------


def test_parser_accepts_valid_structure():
    structure = structure_from_payload()
    assert structure.summary.startswith("Andres llega")
    assert [s.number for s in structure.scenes] == [1, 2, 3, 4]


def test_parser_rejects_fewer_than_min_scenes():
    payload = valid_chapter_payload()
    payload["chapter"]["scenes"] = payload["chapter"]["scenes"][: MIN_SCENES - 1]
    with pytest.raises(Exception):
        ChapterOutput.model_validate(payload)


def test_parser_rejects_single_beat_per_scene():
    payload = valid_chapter_payload()
    payload["chapter"]["scenes"][0]["beats"] = payload["chapter"]["scenes"][0][
        "beats"
    ][: MIN_BEATS_PER_SCENE - 1]
    with pytest.raises(Exception):
        ChapterOutput.model_validate(payload)


def test_parser_rejects_scene_number_gap():
    payload = valid_chapter_payload()
    payload["chapter"]["scenes"][3]["number"] = 5
    with pytest.raises(Exception):
        ChapterOutput.model_validate(payload)


def test_parser_rejects_beat_number_gap():
    payload = valid_chapter_payload()
    payload["chapter"]["scenes"][0]["beats"][1]["number"] = 5
    with pytest.raises(Exception):
        ChapterOutput.model_validate(payload)


def test_parser_rejects_extra_fields():
    payload = valid_chapter_payload()
    payload["chapter"]["scenes"][0]["dialogo"] = "hola"
    with pytest.raises(Exception):
        ChapterOutput.model_validate(payload)


def test_parser_rejects_more_than_max_scenes():
    payload = valid_chapter_payload()
    base_scene = payload["chapter"]["scenes"][0]
    payload["chapter"]["scenes"] = [
        {**base_scene, "number": i} for i in range(1, MAX_SCENES + 2)
    ]
    with pytest.raises(Exception):
        ChapterOutput.model_validate(payload)


def test_parser_rejects_more_than_max_beats():
    payload = valid_chapter_payload()
    beat = payload["chapter"]["scenes"][0]["beats"][0]
    payload["chapter"]["scenes"][0]["beats"] = [
        {**beat, "number": i} for i in range(1, MAX_BEATS_PER_SCENE + 2)
    ]
    with pytest.raises(Exception):
        ChapterOutput.model_validate(payload)


def test_parser_rejects_short_content():
    payload = valid_chapter_payload()
    payload["chapter"]["scenes"][0]["beats"][0]["content"] = "corto"
    with pytest.raises(Exception):
        ChapterOutput.model_validate(payload)


# ---------- Repositorios Scene / Beat ----------


async def _seed_series_season_chapter(session) -> int:
    series = await SeriesRepository(session).create("S")
    season = await SeasonRepository(session).create(series.id, 1)
    chapter = await ChapterRepository(session).create(season.id, 1, logline="Logline del cap 1")
    await session.commit()
    return chapter.id


def test_scene_and_beat_crud(fresh):
    async def body():
        scene_id = beat_id = chapter_id = None
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
            scenes = SceneRepository(session)
            beats = BeatRepository(session)
            scene = await scenes.create(chapter_id, 1, title="E1", summary="Resumen de la escena uno")
            scene_id, beat_id = scene.id, (await beats.create(scene.id, 1, "Andres cruza el umbral de la casa.")).id
            await session.commit()
            got_scene = await scenes.get(scene.id)
            got_beat = await beats.get(beat_id)
            assert got_scene.title == "E1"
            assert got_beat.content.startswith("Andres cruza")
            assert await scenes.next_number(chapter_id) == 2
            assert await beats.next_number(scene.id) == 2
            await scenes.delete(scene.id)
            await session.commit()
        async with make_session_maker(fresh)() as session:
            scenes = SceneRepository(session)
            beats = BeatRepository(session)
            assert await scenes.get(scene_id) is None
            assert await beats.get(beat_id) is None
    run(body())


def test_duplicate_scene_number_integrity_error(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
            scenes = SceneRepository(session)
            await scenes.create(chapter_id, 1)
            with pytest.raises(IntegrityError):
                await scenes.create(chapter_id, 1)
            await session.rollback()
    run(body())


def test_duplicate_beat_number_integrity_error(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
            scenes = SceneRepository(session)
            beats = BeatRepository(session)
            scene = await scenes.create(chapter_id, 1)
            await beats.create(scene.id, 1, "Contenido del primer beat del test.")
            with pytest.raises(IntegrityError):
                await beats.create(scene.id, 1, "Contenido duplicado del segundo beat.")
            await session.rollback()
    run(body())


def test_cascade_chapter_deletes_scenes_and_beats(fresh):
    async def body():
        chapter_id = scene_id = None
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
            scenes = SceneRepository(session)
            beats = BeatRepository(session)
            scene = await scenes.create(chapter_id, 1, summary="Escena que sera borrada en cascada")
            scene_id = scene.id
            await beats.create(scene.id, 1, "Beat que sera borrado en cascada.")
            await session.commit()
            await ChapterRepository(session).delete(chapter_id)
            await session.commit()
        async with make_session_maker(fresh)() as session:
            assert await SceneRepository(session).get(scene_id) is None
            assert await SceneRepository(session).list_by_chapter(chapter_id) == []
    run(body())


def test_chapter_two_axis_status_transitions(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
            repo = ChapterRepository(session)
            chapter = await repo.update_narrative_status(chapter_id, "narrative_complete")
            await session.commit()
            assert chapter.narrative_status == "narrative_complete"
            assert chapter.visual_status == "not_started"
            chapter = await repo.update_visual_status(chapter_id, "visualizing")
            await session.commit()
            assert chapter.visual_status == "visualizing"
            await session.rollback()
    run(body())


def test_chapter_invalid_narrative_status_integrity_error(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
            repo = ChapterRepository(session)
            with pytest.raises(IntegrityError):
                await repo.update_narrative_status(chapter_id, "estado-inventado")
            await session.rollback()
    run(body())


# ---------- ContextBuilder v1 ----------


def test_context_builder_assembles_structure_context(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            series = await SeriesRepository(session).create(
                "Mi Serie", bible={"tone": "drama"}, max_chapters_per_season=20
            )
            season = await SeasonRepository(session).create(series.id, 1)
            await ChapterRepository(session).create(season.id, 1, logline="Logline uno")
            ch2 = await ChapterRepository(session).create(season.id, 2, logline="Logline dos")
            await session.commit()
            context = await ContextBuilder(session).build_chapter_context(ch2.id)
            assert context["series_name"] == "Mi Serie"
            assert context["bible"] == {"tone": "drama"}
            assert context["chapter_logline"] == "Logline dos"
            assert context["previous_chapters"] == [
                {"number": 1, "logline": "Logline uno", "narrative_status": "planned"}
            ]
            assert context["chapter_number"] == 2
    run(body())


# ---------- ChapterService ----------


def test_develop_chapter_persists_and_transitions(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
            provider = FakeProvider(structure=structure_from_payload())
            service = ChapterService(session, provider)
            chapter = await service.develop_chapter(chapter_id)
            assert chapter.narrative_status == "narrative_complete"
            scenes = await SceneRepository(session).list_by_chapter(chapter_id)
            assert [s.number for s in scenes] == [1, 2, 3, 4]
            beats = await BeatRepository(session).list_by_scene(scenes[0].id)
            assert [b.number for b in beats] == [1, 2]
            assert "LOGLINE" in provider.last_prompt
            assert "Logline del cap 1" in provider.last_prompt
    run(body())


def test_develop_chapter_requires_planned_state(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
            repo = ChapterRepository(session)
            await repo.update_narrative_status(chapter_id, "narrative_complete")
            await session.commit()
            service = ChapterService(session, FakeProvider(structure=structure_from_payload()))
            with pytest.raises(NarrativeStateError):
                await service.develop_chapter(chapter_id)
    run(body())


def test_develop_chapter_atomic_on_llm_failure(fresh):
    async def body():
        chapter_id = None
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
        provider = FakeProvider(error=LLMResponseError("salida invalida"))
        async with make_session_maker(fresh)() as session:
            service = ChapterService(session, provider)
            with pytest.raises(LLMResponseError):
                await service.develop_chapter(chapter_id)
        async with make_session_maker(fresh)() as session:
            chapter = await ChapterRepository(session).get(chapter_id)
            assert chapter.narrative_status == "planned"
            assert await SceneRepository(session).list_by_chapter(chapter_id) == []
    run(body())


def test_approve_narrative_full_chapter(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
            service = ChapterService(session, FakeProvider(structure=structure_from_payload()))
            await service.develop_chapter(chapter_id)
            chapter = await service.approve_narrative(chapter_id)
            assert chapter.narrative_status == "narrative_approved"
    run(body())


def test_approve_rejects_uncompleted_chapter(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapter_id = await _seed_series_season_chapter(session)
            service = ChapterService(session, FakeProvider())
            with pytest.raises(NarrativeStateError):
                await service.approve_narrative(chapter_id)
    run(body())
