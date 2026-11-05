"""
Application configuration for Intent Operating Layer (IOL).
Utilizes pydantic-settings to manage environment variables, database connections,
security limits, and CORS origins.
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "Intent Operating Layer"
    app_version: str = "0.3.0"
    environment: str = Field(default="development", alias="IOL_ENV")
    debug: bool = Field(default=False, alias="IOL_DEBUG")

    host: str = Field(default="0.0.0.0", alias="IOL_HOST")
    port: int = Field(default=8000, alias="IOL_PORT")

    database_url: str = Field(default="sqlite:///./iol_tasks.db", alias="DATABASE_URL")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        alias="CORS_ORIGINS"
    )

    # Execution Budget Limits
    default_max_duration_seconds: float = 300.0
    default_max_steps: int = 20
    default_max_cost_usd: float = 1.0

    # Security boundaries
    allow_live_email_dispatch: bool = False  # Cryptographic approval gateway strictly blocks autonomous dispatch
    max_response_bytes: int = 2_000_000

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


settings = Settings()
