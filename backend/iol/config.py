"""
IOL (Intent Operating Layer) - Global Configuration Settings.
Handles database connections, background worker settings, and security flags.
"""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for Intent Operating Layer."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"

    # Database Configuration: PostgreSQL preferred; defaults to SQLite WAL
    # E.g. postgresql+psycopg://postgres:password@localhost:5432/iol_db
    DATABASE_URL: Optional[str] = Field(default=None)
    SQLITE_DB_PATH: Path = DATA_DIR / "iol_tasks.db"

    # Worker Settings
    WORKER_CONCURRENCY: int = 4
    WORKER_POLL_INTERVAL_SECONDS: float = 0.5
    DEFAULT_MAX_DURATION_SECONDS: float = 300.0
    DEFAULT_MAX_STEPS: int = 20
    DEFAULT_MAX_COST_USD: float = 1.0
    DEFAULT_RETRY_LIMIT: int = 2

    # Outreach Engine Path (for adapter inspection if available)
    OUTREACH_ENGINE_PATH: Optional[Path] = Field(
        default=Path(r"C:\Workspace\Projects\Outreach Intelligence Engine")
    )

    # Operator Timezone
    OPERATOR_TIMEZONE: str = "Asia/Kolkata"

    # API Settings
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"]


settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
