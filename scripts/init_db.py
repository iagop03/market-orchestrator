"""One-off script: apply pending Alembic migrations for the configured DATABASE_URL.

Safe to run repeatedly — Alembic only applies migrations not yet recorded as applied,
so this also doubles as "bring an existing DB up to date" after a schema change.
"""
from pathlib import Path

from alembic import command
from alembic.config import Config

from orchestrator.config import Settings

if __name__ == "__main__":
    settings = Settings()
    repo_root = Path(__file__).resolve().parent.parent
    cfg = Config(str(repo_root / "alembic.ini"))
    command.upgrade(cfg, "head")
    print(f"Migrated schema at {settings.database_url}")
