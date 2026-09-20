"""One-off script: create tables for the configured DATABASE_URL."""

from orchestrator.config import Settings
from orchestrator.database import init_db

if __name__ == "__main__":
    settings = Settings()
    init_db(settings.database_url)
    print(f"Initialized schema at {settings.database_url}")
