"""Repositorios para persistir y consultar roadmaps en SQLite."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy import delete
from sqlmodel import Session, select

from roadmap_ai.models import (
    Resource,
    ResourceType,
    Roadmap,
    RoadmapLevel,
    RoadmapSummary,
    UserProgress,
    new_id,
    slugify,
    utc_now,
)
from roadmap_ai.storage.database import (
    Database,
    ResourceRecord,
    RoadmapLevelRecord,
    RoadmapRecord,
    RoadmapResourceRecord,
    SourceCacheRecord,
    TopicRecord,
    UserProgressRecord,
)

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Error base de la capa de persistencia."""


class RoadmapNotFoundError(RepositoryError):
    """El roadmap solicitado no existe."""


class AmbiguousRoadmapIdError(RepositoryError):
    """El prefijo de identificador coincide con más de un roadmap."""


class LevelNotFoundError(RepositoryError):
    """El nivel solicitado no existe en el roadmap."""


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _resource_to_record(resource: Resource) -> ResourceRecord:
    return ResourceRecord(
        id=resource.id,
        type=resource.type.value,
        title=resource.title,
        authors=list(resource.authors),
        year=resource.year,
        url=resource.url,
        doi=resource.doi,
        source=resource.source,
        summary=resource.summary,
        open_access=resource.open_access,
        relevance_score=resource.relevance_score,
        citation_count=resource.citation_count,
        raw_metadata=dict(resource.raw_metadata),
    )


def _record_to_resource(record: ResourceRecord) -> Resource:
    return Resource(
        id=record.id,
        type=ResourceType(record.type),
        title=record.title,
        authors=list(record.authors or []),
        year=record.year,
        url=record.url,
        doi=record.doi,
        source=record.source,
        summary=record.summary,
        open_access=record.open_access,
        relevance_score=record.relevance_score,
        citation_count=record.citation_count,
        raw_metadata=dict(record.raw_metadata or {}),
    )


class SourceCacheRepository:
    """Caché simple y persistente para resultados de conectores."""

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _key(source: str, query: str, limit: int) -> str:
        raw = f"{source}\0{query.strip().casefold()}\0{limit}".encode()
        return hashlib.sha256(raw).hexdigest()

    def get(self, source: str, query: str, limit: int) -> list[Resource] | None:
        """Devuelve recursos cacheados vigentes o ``None`` si no hay entrada."""
        key = self._key(source, query, limit)
        with self.database.session() as session:
            record = session.get(SourceCacheRecord, key)
            if record is None:
                return None
            if _as_utc(record.expires_at) <= utc_now():
                session.delete(record)
                logger.debug("Caché expirada: fuente=%s", source)
                return None
            try:
                resources = [Resource.model_validate(item) for item in record.payload]
            except (ValidationError, TypeError):
                session.delete(record)
                logger.warning("Entrada de caché inválida descartada: fuente=%s", source)
                return None
            logger.debug(
                "Caché utilizada: fuente=%s query=%r resultados=%d",
                source,
                query,
                len(resources),
            )
            return resources

    def set(
        self,
        source: str,
        query: str,
        limit: int,
        resources: list[Resource],
        ttl_seconds: int,
    ) -> None:
        """Guarda o reemplaza una entrada de caché con TTL."""
        if ttl_seconds <= 0:
            return

        key = self._key(source, query, limit)
        now = utc_now()
        with self.database.session() as session:
            record = session.get(SourceCacheRecord, key)
            if record is None:
                record = SourceCacheRecord(
                    key=key,
                    source=source,
                    query=query,
                    limit=limit,
                    payload=[],
                    created_at=now,
                    expires_at=now + timedelta(seconds=ttl_seconds),
                )
            record.query = query
            record.limit = limit
            record.payload = [resource.model_dump(mode="json") for resource in resources]
            record.created_at = now
            record.expires_at = now + timedelta(seconds=ttl_seconds)
            session.add(record)
        logger.debug(
            "Caché actualizada: fuente=%s query=%r resultados=%d ttl=%ss",
            source,
            query,
            len(resources),
            ttl_seconds,
        )

    def clear(self, source: str | None = None) -> int:
        """Elimina entradas de caché y devuelve cuántas se borraron."""
        with self.database.session() as session:
            statement = select(SourceCacheRecord)
            if source is not None:
                statement = statement.where(SourceCacheRecord.source == source)
            records = session.exec(statement).all()
            for record in records:
                session.delete(record)
            return len(records)


class RoadmapRepository:
    """Acceso de alto nivel a roadmaps, niveles, recursos y progreso."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def save(self, roadmap: Roadmap) -> Roadmap:
        """Inserta o actualiza un roadmap completo y sus relaciones."""
        unique_resources: dict[str, Resource] = {
            resource.id: resource for resource in roadmap.resources
        }
        for level in roadmap.levels:
            for resource in level.resources:
                unique_resources.setdefault(resource.id, resource)

        with self.database.session() as session:
            topic = session.exec(
                select(TopicRecord).where(TopicRecord.slug == slugify(roadmap.topic))
            ).first()
            if topic is None:
                topic = TopicRecord(
                    id=new_id(),
                    name=roadmap.topic,
                    slug=slugify(roadmap.topic),
                    created_at=roadmap.created_at,
                )
                session.add(topic)
            else:
                topic.name = roadmap.topic
                session.add(topic)
            session.flush()

            record = session.get(RoadmapRecord, roadmap.id)
            if record is None:
                record = RoadmapRecord(
                    id=roadmap.id,
                    topic_id=topic.id,
                    topic=roadmap.topic,
                    title=roadmap.title,
                    description=roadmap.description,
                    queries_used=list(roadmap.queries_used),
                    created_at=roadmap.created_at,
                    updated_at=roadmap.updated_at,
                )
                session.add(record)
            else:
                record.topic_id = topic.id
                record.topic = roadmap.topic
                record.title = roadmap.title
                record.description = roadmap.description
                record.queries_used = list(roadmap.queries_used)
                record.updated_at = roadmap.updated_at
                session.add(record)
            session.flush()

            session.exec(
                delete(RoadmapResourceRecord).where(RoadmapResourceRecord.roadmap_id == roadmap.id)
            )
            session.exec(
                delete(RoadmapLevelRecord).where(RoadmapLevelRecord.roadmap_id == roadmap.id)
            )
            session.flush()

            for resource in unique_resources.values():
                existing_resource = session.get(ResourceRecord, resource.id)
                replacement = _resource_to_record(resource)
                if existing_resource is None:
                    session.add(replacement)
                else:
                    for field_name in ResourceRecord.model_fields:
                        setattr(existing_resource, field_name, getattr(replacement, field_name))
                    session.add(existing_resource)

            for level in roadmap.levels:
                level_record = RoadmapLevelRecord(
                    id=new_id(),
                    roadmap_id=roadmap.id,
                    number=level.number,
                    title=level.title,
                    objective=level.objective,
                    prerequisites=list(level.prerequisites),
                    concepts=list(level.concepts),
                    projects=list(level.projects),
                )
                session.add(level_record)
                session.flush()

                level_resources = {resource.id: resource for resource in level.resources}
                for position, resource in enumerate(level_resources.values()):
                    session.add(
                        RoadmapResourceRecord(
                            id=new_id(),
                            roadmap_id=roadmap.id,
                            level_id=level_record.id,
                            level_number=level.number,
                            resource_id=resource.id,
                            position=position,
                        )
                    )

        logger.info(
            "Roadmap guardado: id=%s, niveles=%d, recursos=%d",
            roadmap.id,
            len(roadmap.levels),
            len(unique_resources),
        )
        return roadmap

    def get(self, roadmap_id: str) -> Roadmap | None:
        """Recupera un roadmap completo o ``None`` si no existe."""
        with self.database.session() as session:
            record = session.get(RoadmapRecord, roadmap_id)
            if record is None:
                return None

            level_records = session.exec(
                select(RoadmapLevelRecord)
                .where(RoadmapLevelRecord.roadmap_id == roadmap_id)
                .order_by(RoadmapLevelRecord.number)
            ).all()
            links = session.exec(
                select(RoadmapResourceRecord)
                .where(RoadmapResourceRecord.roadmap_id == roadmap_id)
                .order_by(RoadmapResourceRecord.position)
            ).all()

            resource_ids = {link.resource_id for link in links}
            resource_records = (
                session.exec(
                    select(ResourceRecord).where(ResourceRecord.id.in_(resource_ids))
                ).all()
                if resource_ids
                else []
            )
            resource_map = {
                resource_record.id: _record_to_resource(resource_record)
                for resource_record in resource_records
            }
            links_by_level: dict[str, list[RoadmapResourceRecord]] = {}
            for link in links:
                links_by_level.setdefault(link.level_id, []).append(link)

            levels: list[RoadmapLevel] = []
            for level_record in level_records:
                level_resources = [
                    resource_map[link.resource_id]
                    for link in sorted(
                        links_by_level.get(level_record.id, []),
                        key=lambda item: item.position,
                    )
                    if link.resource_id in resource_map
                ]
                levels.append(
                    RoadmapLevel(
                        number=level_record.number,
                        title=level_record.title,
                        objective=level_record.objective,
                        prerequisites=list(level_record.prerequisites or []),
                        concepts=list(level_record.concepts or []),
                        projects=list(level_record.projects or []),
                        resources=level_resources,
                    )
                )

            return Roadmap(
                id=record.id,
                topic=record.topic,
                title=record.title,
                description=record.description,
                levels=levels,
                queries_used=list(record.queries_used or []),
                created_at=_as_utc(record.created_at),
                updated_at=_as_utc(record.updated_at),
            )

    def list_summaries(self, limit: int = 100) -> list[RoadmapSummary]:
        """Lista roadmaps ordenados por última actualización."""
        with self.database.session() as session:
            records = session.exec(
                select(RoadmapRecord).order_by(RoadmapRecord.updated_at.desc()).limit(limit)
            ).all()
            summaries: list[RoadmapSummary] = []
            for record in records:
                level_ids = session.exec(
                    select(RoadmapLevelRecord.id).where(RoadmapLevelRecord.roadmap_id == record.id)
                ).all()
                completed_levels = session.exec(
                    select(UserProgressRecord.level_number)
                    .where(
                        UserProgressRecord.roadmap_id == record.id,
                        UserProgressRecord.completed.is_(True),
                    )
                    .order_by(UserProgressRecord.level_number)
                ).all()
                resource_ids = session.exec(
                    select(RoadmapResourceRecord.resource_id).where(
                        RoadmapResourceRecord.roadmap_id == record.id
                    )
                ).all()
                summaries.append(
                    RoadmapSummary(
                        id=record.id,
                        topic=record.topic,
                        title=record.title,
                        description=record.description,
                        total_levels=len(level_ids),
                        resource_count=len(set(resource_ids)),
                        completed_levels=list(completed_levels),
                        created_at=_as_utc(record.created_at),
                        updated_at=_as_utc(record.updated_at),
                    )
                )
            return summaries

    def resolve_id(self, identifier: str) -> str:
        """Resuelve un UUID completo o un prefijo único."""
        candidate = identifier.strip()
        if not candidate:
            raise RoadmapNotFoundError("El identificador no puede estar vacío")

        with self.database.session() as session:
            if session.get(RoadmapRecord, candidate) is not None:
                return candidate

            matches = session.exec(
                select(RoadmapRecord.id).where(RoadmapRecord.id.startswith(candidate)).limit(2)
            ).all()

        if not matches:
            raise RoadmapNotFoundError(f"No existe un roadmap con id '{identifier}'")
        if len(matches) > 1:
            raise AmbiguousRoadmapIdError(
                f"El prefijo '{identifier}' coincide con varios roadmaps; usa un id más largo"
            )
        return matches[0]

    def get_progress(self, roadmap_id: str) -> list[UserProgress]:
        """Devuelve el estado de progreso registrado para un roadmap."""
        with self.database.session() as session:
            self._require_roadmap(session, roadmap_id)
            records = session.exec(
                select(UserProgressRecord)
                .where(UserProgressRecord.roadmap_id == roadmap_id)
                .order_by(UserProgressRecord.level_number)
            ).all()
            return [
                UserProgress(
                    roadmap_id=record.roadmap_id,
                    level_number=record.level_number,
                    completed=record.completed,
                    completed_at=_as_utc(record.completed_at) if record.completed_at else None,
                )
                for record in records
            ]

    def get_completed_levels(self, roadmap_id: str) -> list[int]:
        """Devuelve los números de nivel completados."""
        return [
            progress.level_number
            for progress in self.get_progress(roadmap_id)
            if progress.completed
        ]

    def set_level_completed(
        self,
        roadmap_id: str,
        level_number: int,
        completed: bool = True,
    ) -> UserProgress:
        """Marca o desmarca un nivel como completado."""
        with self.database.session() as session:
            self._require_roadmap(session, roadmap_id)
            level = session.exec(
                select(RoadmapLevelRecord).where(
                    RoadmapLevelRecord.roadmap_id == roadmap_id,
                    RoadmapLevelRecord.number == level_number,
                )
            ).first()
            if level is None:
                raise LevelNotFoundError(
                    f"El roadmap {roadmap_id} no tiene un nivel {level_number}"
                )

            progress = session.exec(
                select(UserProgressRecord).where(
                    UserProgressRecord.roadmap_id == roadmap_id,
                    UserProgressRecord.level_number == level_number,
                )
            ).first()
            if progress is None:
                progress = UserProgressRecord(
                    id=new_id(),
                    roadmap_id=roadmap_id,
                    level_number=level_number,
                )

            progress.completed = completed
            progress.completed_at = utc_now() if completed else None
            session.add(progress)
            session.flush()

            logger.info(
                "Progreso actualizado: roadmap=%s nivel=%d completado=%s",
                roadmap_id,
                level_number,
                completed,
            )
            return UserProgress(
                roadmap_id=progress.roadmap_id,
                level_number=progress.level_number,
                completed=progress.completed,
                completed_at=(_as_utc(progress.completed_at) if progress.completed_at else None),
            )

    @staticmethod
    def _require_roadmap(session: Session, roadmap_id: str) -> RoadmapRecord:
        record = session.get(RoadmapRecord, roadmap_id)
        if record is None:
            raise RoadmapNotFoundError(f"No existe un roadmap con id '{roadmap_id}'")
        return record


__all__ = [
    "AmbiguousRoadmapIdError",
    "LevelNotFoundError",
    "RepositoryError",
    "RoadmapNotFoundError",
    "RoadmapRepository",
    "SourceCacheRepository",
]
