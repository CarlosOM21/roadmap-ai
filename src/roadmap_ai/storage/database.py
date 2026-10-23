"""Motor SQLite, tablas SQLModel y utilidades de sesión."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Column, UniqueConstraint, create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Session, SQLModel

from roadmap_ai.models import utc_now

logger = logging.getLogger(__name__)


class TopicRecord(SQLModel, table=True):
    """Tabla de temas académicos."""

    __tablename__ = "topics"

    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=utc_now)


class RoadmapRecord(SQLModel, table=True):
    """Tabla principal de roadmaps."""

    __tablename__ = "roadmaps"

    id: str = Field(primary_key=True)
    topic_id: str = Field(foreign_key="topics.id", index=True)
    topic: str = Field(index=True)
    title: str
    description: str = ""
    queries_used: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, index=True)


class ResourceRecord(SQLModel, table=True):
    """Tabla de recursos recuperados de fuentes legales."""

    __tablename__ = "resources"

    id: str = Field(primary_key=True)
    type: str = Field(index=True)
    title: str = Field(index=True)
    authors: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    year: int | None = Field(default=None, index=True)
    url: str = Field(index=True)
    doi: str | None = Field(default=None, index=True)
    source: str = Field(index=True)
    summary: str = ""
    open_access: bool = Field(default=False, index=True)
    relevance_score: float = Field(default=0.0)
    citation_count: int | None = None
    raw_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class RoadmapLevelRecord(SQLModel, table=True):
    """Tabla de niveles asociados a un roadmap."""

    __tablename__ = "roadmap_levels"
    __table_args__ = (UniqueConstraint("roadmap_id", "number", name="uq_roadmap_level_number"),)

    id: str = Field(primary_key=True)
    roadmap_id: str = Field(foreign_key="roadmaps.id", index=True)
    number: int = Field(index=True)
    title: str
    objective: str = ""
    prerequisites: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    concepts: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    projects: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )


class RoadmapResourceRecord(SQLModel, table=True):
    """Tabla de relación entre niveles y recursos."""

    __tablename__ = "roadmap_resources"
    __table_args__ = (UniqueConstraint("level_id", "resource_id", name="uq_level_resource"),)

    id: str = Field(primary_key=True)
    roadmap_id: str = Field(foreign_key="roadmaps.id", index=True)
    level_id: str = Field(foreign_key="roadmap_levels.id", index=True)
    level_number: int = Field(index=True)
    resource_id: str = Field(foreign_key="resources.id", index=True)
    position: int = Field(default=0, ge=0)
    rationale: str = ""


class UserProgressRecord(SQLModel, table=True):
    """Tabla de progreso del usuario por nivel."""

    __tablename__ = "user_progress"
    __table_args__ = (
        UniqueConstraint("roadmap_id", "level_number", name="uq_roadmap_level_progress"),
    )

    id: str = Field(primary_key=True)
    roadmap_id: str = Field(foreign_key="roadmaps.id", index=True)
    level_number: int = Field(index=True)
    completed: bool = Field(default=False, index=True)
    completed_at: datetime | None = None


class SourceCacheRecord(SQLModel, table=True):
    """Caché persistente de resultados normalizados por fuente y consulta."""

    __tablename__ = "source_cache"

    key: str = Field(primary_key=True)
    source: str = Field(index=True)
    query: str
    limit: int = Field(ge=1)
    payload: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(index=True)


def _is_memory_database(url: str) -> bool:
    parsed = make_url(url)
    return parsed.get_backend_name() == "sqlite" and parsed.database in {None, "", ":memory:"}


class Database:
    """Gestiona el engine SQLAlchemy y el ciclo de vida de las sesiones."""

    def __init__(self, database_url: str) -> None:
        self.source_url = database_url
        self.engine = self._create_engine(database_url)

    @staticmethod
    def _create_engine(database_url: str) -> Engine:
        parsed = make_url(database_url)
        engine_kwargs: dict[str, Any] = {"echo": False}

        if parsed.get_backend_name() == "sqlite":
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if _is_memory_database(database_url):
                engine_kwargs["poolclass"] = StaticPool
            elif parsed.database:
                database_path = Path(parsed.database).expanduser()
                if not database_path.is_absolute():
                    database_path = (Path.cwd() / database_path).resolve()
                database_path.parent.mkdir(parents=True, exist_ok=True)
                parsed = parsed.set(database=str(database_path))

        engine = create_engine(parsed, **engine_kwargs)

        if parsed.get_backend_name() == "sqlite":

            @event.listens_for(engine, "connect")
            def _enable_foreign_keys(dbapi_connection: Any, _: Any) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        return engine

    @property
    def database_url(self) -> str:
        """URL efectiva del engine, útil para diagnósticos."""
        return str(self.engine.url)

    def create_all(self) -> None:
        """Crea todas las tablas si no existen."""
        SQLModel.metadata.create_all(self.engine)
        logger.debug("Esquema de base de datos asegurado en %s", self.database_url)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Abre una sesión con commit automático y rollback ante errores."""
        with Session(self.engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("Error de base de datos; se revirtió la transacción")
                raise

    def dispose(self) -> None:
        """Libera las conexiones del engine."""
        self.engine.dispose()

    def __enter__(self) -> Database:
        self.create_all()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.dispose()


__all__ = [
    "Database",
    "ResourceRecord",
    "RoadmapLevelRecord",
    "RoadmapRecord",
    "RoadmapResourceRecord",
    "SourceCacheRecord",
    "TopicRecord",
    "UserProgressRecord",
]
