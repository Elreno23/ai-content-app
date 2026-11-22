import subprocess
import sys


def run_alembic(args):
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
        cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]),
    )


def test_history_contains_single_baseline():
    result = run_alembic(["history"])
    assert result.returncode == 0
    assert "0001_baseline_narrative" in result.stdout


def test_current_is_head():
    result = run_alembic(["current"])
    assert result.returncode == 0
    assert "0002_h3_1_structure (head)" in result.stdout


def test_upgrade_sql_matches_real_schema():
    result = run_alembic(["upgrade", "head", "--sql"])
    assert result.returncode == 0
    sql = result.stdout
    assert "CREATE TABLE narrative" in sql
    assert "id SERIAL NOT NULL" in sql
    assert "episode_number INTEGER NOT NULL" in sql
    assert "create_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in sql
    assert "payload JSONB NOT NULL" in sql
    assert "CREATE INDEX ix_narrative_id" in sql
    assert "CREATE UNIQUE INDEX ix_narrative_episode_number" in sql


def test_history_contains_h3_1_structure():
    result = run_alembic(["history"])
    assert result.returncode == 0
    assert "0002_h3_1_structure" in result.stdout


def test_upgrade_sql_contains_h3_1_tables():
    result = run_alembic(["upgrade", "head", "--sql"])
    assert result.returncode == 0
    sql = result.stdout
    for table in ("series", "seasons", "chapters"):
        assert f"CREATE TABLE {table}" in sql
        assert f"{table} (\n    id SERIAL NOT NULL" in sql
    assert "FOREIGN KEY(series_id) REFERENCES series (id) ON DELETE CASCADE" in sql
    assert "FOREIGN KEY(season_id) REFERENCES seasons (id) ON DELETE CASCADE" in sql
    assert "uq_seasons_series_number UNIQUE (series_id, number)" in sql
    assert "uq_chapters_season_number UNIQUE (season_id, number)" in sql
    assert "ck_series_max_chapters_positive CHECK" in sql
    assert "ck_seasons_number_positive CHECK (number >= 1)" in sql
    assert "ck_chapters_number_positive CHECK (number >= 1)" in sql
    assert "logline TEXT" in sql
    assert "status VARCHAR(50) NOT NULL" in sql
