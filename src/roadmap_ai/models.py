"""Modelos de dominio de RoadmapAI.

Los modelos Pydantic describen la información que circula por el pipeline y que
se exporta al usuario. La persistencia se implementa por separado con SQLModel
en :mod:`roadmap_ai.storage.database`.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RESOURCE_TYPES = ("book", "course", "paper", "documentation", "video", "tool")


def utc_now() -> datetime:
    """Devuelve la fecha y hora actual en UTC con zona horaria."""
    return datetime.now(UTC)


def new_id() -> str:
    """Genera un identificador UUID seguro para las entidades."""
    return str(uuid4())


def slugify(value: str) -> str:
    """Convierte un texto en un slug ASCII apto para URLs e identificadores."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")[:100] or "tema"


class ResourceType(StrEnum):
    """Tipos de recurso admitidos por el producto."""

    BOOK = "book"
    COURSE = "course"
    PAPER = "paper"
    DOCUMENTATION = "documentation"
    VIDEO = "video"
    TOOL = "tool"


class Topic(BaseModel):
    """Tema académico sobre el que se construye un roadmap."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(default_factory=new_id)
    name: str = Field(min_length=1, max_length=200)
    slug: str = ""
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El nombre del tema no puede estar vacío")
        return value

    @model_validator(mode="after")
    def _complete_slug(self) -> Topic:
        if not self.slug:
            self.slug = slugify(self.name)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.slug):
            raise ValueError("El slug debe contener solo minúsculas, números y guiones")
        return self


class Resource(BaseModel):
    """Recurso académico con procedencia y URL verificable."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(default_factory=new_id)
    type: ResourceType
    title: str = Field(min_length=1, max_length=500)
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1000, le=2200)
    url: str
    doi: str | None = None
    source: str = Field(min_length=1, max_length=100)
    summary: str = ""
    open_access: bool = False
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    citation_count: int | None = Field(default=None, ge=0)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "source")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El campo no puede estar vacío")
        return value

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("La URL debe ser HTTP(S) y contener un dominio")
        return value

    @field_validator("doi")
    @classmethod
    def _normalize_doi(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = re.sub(
            r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)",
            "",
            value.strip(),
            flags=re.I,
        )
        if not normalized:
            return None
        return normalized.lower()

    @field_validator("authors")
    @classmethod
    def _clean_authors(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for author in value:
            name = author.strip()
            if name and name.casefold() not in seen:
                cleaned.append(name)
                seen.add(name.casefold())
        return cleaned


class RoadmapLevel(BaseModel):
    """Nivel progresivo de un roadmap."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    objective: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)


class Roadmap(BaseModel):
    """Roadmap completo generado para un tema."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(default_factory=new_id)
    topic: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=250)
    description: str = ""
    levels: list[RoadmapLevel] = Field(min_length=1)
    resources: list[Resource] = Field(default_factory=list)
    queries_used: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate_levels_and_resources(self) -> Roadmap:
        numbers = [level.number for level in self.levels]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Los números de nivel no pueden repetirse")

        unique_resources: dict[str, Resource] = {
            resource.id: resource for resource in self.resources
        }
        for level in self.levels:
            for resource in level.resources:
                unique_resources.setdefault(resource.id, resource)
        self.resources = list(unique_resources.values())
        return self


class RoadmapSummary(BaseModel):
    """Resumen de roadmap usado en listados de la CLI."""

    model_config = ConfigDict(extra="forbid")

    id: str
    topic: str
    title: str
    description: str = ""
    total_levels: int = Field(ge=0)
    resource_count: int = Field(ge=0)
    completed_levels: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @property
    def progress_percent(self) -> int:
        """Porcentaje entero de niveles completados."""
        if self.total_levels == 0:
            return 0
        return round(len(self.completed_levels) / self.total_levels * 100)


class UserProgress(BaseModel):
    """Estado persistido de un nivel para un roadmap."""

    model_config = ConfigDict(extra="forbid")

    roadmap_id: str
    level_number: int = Field(ge=1)
    completed: bool
    completed_at: datetime | None = None


class SourceResult(BaseModel):
    """Resultado normalizado de la consulta a una fuente académica."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    resources: list[Resource] = Field(default_factory=list)
    error: str | None = None
    response_time_ms: float = Field(default=0.0, ge=0.0)

    @property
    def success(self) -> bool:
        """Indica si la consulta terminó sin error."""
        return self.error is None


__all__ = [
    "RESOURCE_TYPES",
    "Resource",
    "ResourceType",
    "Roadmap",
    "RoadmapLevel",
    "RoadmapSummary",
    "SourceResult",
    "Topic",
    "UserProgress",
    "new_id",
    "slugify",
    "utc_now",
]
