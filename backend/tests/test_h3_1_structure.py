import asyncio
import os
import urllib.parse

import psycopg2
import pytest
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.base import Base
from app.models.chapter import Chapter
from app.models.season import Season
from app.models.series import Series
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.season_repository import SeasonRepository
from app.repositories.series_repository import SeriesRepository

load_dotenv()
DEV_URL = os.environ["DATABASE_URL"]
TEST_DB_URL = DEV_URL.rsplit("/", 1)[0] + "/ai_content_test"


def _psycopg2_connect(dbname: str):
    u = urllib.parse.urlparse(DEV_URL.replace("+asyncpg", "+psycopg2"))
    return psycopg2.connect(
        dbname=dbname,
        user=u.username,
        password=u.password,
        host=u.hostname,
        port=u.port,
    )


@pytest.fixture(scope="module")
def test_db_url():
    conn = _psycopg2_connect("postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP DATABASE IF EXISTS ai_content_test")
    cur.execute("CREATE DATABASE ai_content_test")
    conn.close()
    yield TEST_DB_URL
    conn = _psycopg2_connect("postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = 'ai_content_test' AND pid <> pg_backend_pid()"
    )
    cur.execute("DROP DATABASE ai_content_test")
    conn.close()


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def fresh(test_db_url):
    """Engine efímero por test: esquema limpio, NullPool, un event loop por test."""
    async def _setup():
        engine = create_async_engine(test_db_url, poolclass=NullPool, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        return engine
    engine = run(_setup())
    yield engine
    run(engine.dispose())


def make_session_maker(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


def test_create_and_get_series(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            repo = SeriesRepository(session)
            created = await repo.create("Mi Serie", bible={"tone": "drama"}, max_chapters_per_season=20)
            await session.commit()
            fetched = await repo.get(created.id)
            assert fetched is not None
            assert fetched.name == "Mi Serie"
            assert fetched.bible == {"tone": "drama"}
            assert fetched.max_chapters_per_season == 20
            assert fetched.created_at is not None
    run(body())


def test_list_all_series(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            repo = SeriesRepository(session)
            await repo.create("A")
            await repo.create("B")
            await session.commit()
            assert [s.name for s in await repo.list_all()] == ["A", "B"]
    run(body())


def test_update_series(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            repo = SeriesRepository(session)
            created = await repo.create("Original")
            await session.commit()
            await repo.update(created.id, name="Modificada", max_chapters_per_season=10)
            await session.commit()
            fetched = await repo.get(created.id)
            assert fetched.name == "Modificada"
            assert fetched.max_chapters_per_season == 10
            assert await repo.update(99999, name="x") is None
    run(body())


def test_delete_series(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            repo = SeriesRepository(session)
            created = await repo.create("Temporal")
            await session.commit()
            assert await repo.delete(created.id) is True
            await session.commit()
            assert await repo.get(created.id) is None
            assert await repo.delete(created.id) is False
    run(body())


def test_create_and_get_season(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            seasons = SeasonRepository(session)
            series_repo = SeriesRepository(session)
            series = await series_repo.create("S")
            season = await seasons.create(series.id, 1, title="T1")
            await session.commit()
            fetched = await seasons.get(season.id)
            assert fetched is not None
            assert fetched.series_id == series.id
            assert fetched.number == 1
            assert fetched.title == "T1"
    run(body())


def test_list_by_series_ordered(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            seasons = SeasonRepository(session)
            series_repo = SeriesRepository(session)
            s1 = await series_repo.create("S1")
            s2 = await series_repo.create("S2")
            await seasons.create(s1.id, 2)
            await seasons.create(s1.id, 1)
            await seasons.create(s2.id, 1)
            await session.commit()
            numbers = [se.number for se in await seasons.list_by_series(s1.id)]
            assert numbers == [1, 2]
            assert len(await seasons.list_by_series(s2.id)) == 1
    run(body())


def test_season_next_number(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            seasons = SeasonRepository(session)
            series_repo = SeriesRepository(session)
            series = await series_repo.create("S")
            await session.commit()
            assert await seasons.next_number(series.id) == 1
            await seasons.create(series.id, 1)
            await session.commit()
            assert await seasons.next_number(series.id) == 2
    run(body())


def test_duplicate_season_number_raises_integrity_error(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            seasons = SeasonRepository(session)
            series_repo = SeriesRepository(session)
            series = await series_repo.create("S")
            await seasons.create(series.id, 1)
            with pytest.raises(IntegrityError):
                await seasons.create(series.id, 1)
            await session.rollback()
    run(body())


def test_create_and_get_chapter(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapters = ChapterRepository(session)
            series_repo = SeriesRepository(session)
            seasons = SeasonRepository(session)
            series = await series_repo.create("S")
            season = await seasons.create(series.id, 1)
            chapter = await chapters.create(season.id, 1, title="Piloto", logline="Juan cae")
            await session.commit()
            fetched = await chapters.get(chapter.id)
            assert fetched is not None
            assert fetched.season_id == season.id
            assert fetched.narrative_status == "planned"
            assert fetched.visual_status == "not_started"
            assert fetched.title == "Piloto"
            assert fetched.logline == "Juan cae"
    run(body())


def test_list_by_season_and_status(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapters = ChapterRepository(session)
            series_repo = SeriesRepository(session)
            seasons = SeasonRepository(session)
            series = await series_repo.create("S")
            s1 = await seasons.create(series.id, 1)
            s2 = await seasons.create(series.id, 2)
            await chapters.create(s1.id, 1, logline="a")
            c2 = await chapters.create(s1.id, 2, logline="b")
            await chapters.create(s2.id, 1, logline="c")
            await session.commit()
            await chapters.update_narrative_status(c2.id, "drafting")
            await session.commit()
            assert [c.number for c in await chapters.list_by_season(s1.id)] == [1, 2]
            draft = await chapters.list_by_narrative_status("drafting")
            assert [c.id for c in draft] == [c2.id]
            assert await chapters.list_by_narrative_status("visualizing") == []
    run(body())


def test_chapter_next_number(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapters = ChapterRepository(session)
            series_repo = SeriesRepository(session)
            seasons = SeasonRepository(session)
            series = await series_repo.create("S")
            season = await seasons.create(series.id, 1)
            await session.commit()
            assert await chapters.next_number(season.id) == 1
            await chapters.create(season.id, 1)
            await session.commit()
            assert await chapters.next_number(season.id) == 2
    run(body())


def test_duplicate_chapter_number_raises_integrity_error(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapters = ChapterRepository(session)
            series_repo = SeriesRepository(session)
            seasons = SeasonRepository(session)
            series = await series_repo.create("S")
            season = await seasons.create(series.id, 1)
            await chapters.create(season.id, 1)
            with pytest.raises(IntegrityError):
                await chapters.create(season.id, 1)
            await session.rollback()
    run(body())


def test_max_chapters_zero_raises_integrity_error(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            repo = SeriesRepository(session)
            with pytest.raises(IntegrityError):
                await repo.create("S", max_chapters_per_season=0)
            await session.rollback()
    run(body())


def test_cascade_delete_series(fresh):
    async def body():
        series_id = season_id = None
        async with make_session_maker(fresh)() as session:
            chapters = ChapterRepository(session)
            seasons = SeasonRepository(session)
            series_repo = SeriesRepository(session)
            series = await series_repo.create("S")
            season = await seasons.create(series.id, 1)
            await chapters.create(season.id, 1)
            await session.commit()
            series_id, season_id = series.id, season.id
            await series_repo.delete(series.id)
            await session.commit()
        # verificación en sesión nueva: la identity map no debe ocultar el CASCADE
        async with make_session_maker(fresh)() as session:
            seasons = SeasonRepository(session)
            chapters = ChapterRepository(session)
            assert await seasons.get(season_id) is None
            assert await seasons.list_by_series(series_id) == []
            assert len(await chapters.list_by_season(season_id)) == 0
    run(body())


def test_orm_navigation_series_season(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            seasons = SeasonRepository(session)
            series_repo = SeriesRepository(session)
            series = await series_repo.create("S")
            season = await seasons.create(series.id, 1)
            await session.commit()
            series_id, season_id = series.id, season.id
        async with make_session_maker(fresh)() as session:
            loaded_series = await session.get(Series, series_id)
            assert [s.id for s in loaded_series.seasons] == [season_id]
            loaded_season = await session.get(Season, season_id)
            assert loaded_season.series.id == series_id
            assert loaded_season.series_id == series_id
    run(body())


def test_orm_navigation_season_chapter(fresh):
    async def body():
        async with make_session_maker(fresh)() as session:
            chapters = ChapterRepository(session)
            series_repo = SeriesRepository(session)
            seasons = SeasonRepository(session)
            series = await series_repo.create("S")
            season = await seasons.create(series.id, 1)
            chapter = await chapters.create(season.id, 1)
            await session.commit()
            season_id, chapter_id = season.id, chapter.id
        async with make_session_maker(fresh)() as session:
            loaded_season = await session.get(Season, season_id)
            assert [c.id for c in loaded_season.chapters] == [chapter_id]
            loaded_chapter = await session.get(Chapter, chapter_id)
            assert loaded_chapter.season.id == season_id
            assert loaded_chapter.season_id == season_id
    run(body())
