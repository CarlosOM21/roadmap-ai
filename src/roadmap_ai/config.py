"""Configuración de RoadmapAI cargada desde variables de entorno y `.env`."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración tipada de la aplicación.

    Las claves sensibles usan :class:`~pydantic.SecretStr` para evitar que se
    impriman accidentalmente en logs o mensajes de error.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    llm_provider: str = Field(default="openai", min_length=1)
    llm_api_key: SecretStr | None = None
    llm_model: str = Field(default="gpt-4o-mini", min_length=1)
    openalex_email: str = ""
    semantic_scholar_api_key: SecretStr | None = None
    youtube_api_key: SecretStr | None = None
    database_url: str = "sqlite:///data/roadmaps.db"
    request_timeout: float = Field(default=20.0, gt=0)
    max_retries: int = Field(default=3, ge=0)
    cache_ttl_seconds: int = Field(default=21600, ge=0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la configuración efectiva, cacheada durante el proceso."""
    return Settings()


__all__ = ["Settings", "get_settings"]
