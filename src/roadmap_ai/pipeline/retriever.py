"""Recuperación y deduplicación de recursos (Fase 3)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from roadmap_ai.models import SourceResult
from roadmap_ai.sources.base import Source
from roadmap_ai.storage.database import Database


@runtime_checkable
class Retriever(Protocol):
    """Contrato para consultar varias fuentes y normalizar sus resultados."""

    async def retrieve(
        self,
        queries: Sequence[str],
        sources: Sequence[Source],
        limit: int = 10,
    ) -> list[SourceResult]:
        """Ejecuta las consultas y devuelve resultados por fuente."""
        ...


class MultiSourceRetriever:
    """Orquestador de conectores; se implementará en la Fase 3."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def retrieve(
        self,
        queries: Sequence[str],
        sources: Sequence[Source],
        limit: int = 10,
    ) -> list[SourceResult]:
        """Consulta las fuentes; pendiente de implementación."""
        raise NotImplementedError("El retriever se implementa en la Fase 3")


__all__ = ["MultiSourceRetriever", "Retriever"]
