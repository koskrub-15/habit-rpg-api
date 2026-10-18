import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from apps.db.base import Base

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_alembic(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def migrated_db(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("migrations") / "migrated.db"
    result = run_alembic(db_path, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    return db_path


def test_migrations_create_every_model_table(migrated_db):
    """Production schema comes only from Alembic, so every mapped table must be migrated."""
    with sqlite3.connect(migrated_db) as conn:
        migrated = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    missing = set(Base.metadata.tables) - migrated
    assert not missing, f"Tables without a migration: {sorted(missing)}"


def test_migrations_match_models(migrated_db):
    result = run_alembic(migrated_db, "check")
    assert result.returncode == 0, result.stdout + result.stderr
