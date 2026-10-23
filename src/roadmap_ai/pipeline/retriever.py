"""Recuperación y deduplicación de recursos (Fase 3)."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from urllib.parse import urlparse

from roadmap_ai.models import Resource, SourceResult
from roadmap_ai.sources.base import Source
from roadmap_ai.storage.database import Database
from roadmap_ai.storage.repositories import SourceCacheRepository

logger = logging.getLogger(__name__)


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


def _normalize_url_key(url: str) -> str:
    """Normaliza URL para deduplicación."""
    parsed = urlparse(url)
    # Normalizar esquema y host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    # Remover www.
    if netloc.startswith("www."):
        netloc = netloc[4:]
    # Normalizar path - quitar trailing slash
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    # Para DOI, normalizar
    if netloc == "doi.org" and path:
        path = path.lower()
    return f"{scheme}://{netloc}{path}{('?' + parsed.query) if parsed.query else ''}"


def _normalize_title_key(title: str) -> str:
    """Normaliza título para deduplicación."""
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


class MultiSourceRetriever:
    """Orquestador de conectores con paralelización, deduplicación y manejo de errores."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.cache_repo = SourceCacheRepository(database)

    async def retrieve(
        self,
        queries: Sequence[str],
        sources: Sequence[Source],
        limit: int = 10,
    ) -> list[SourceResult]:
        """Consulta las fuentes en paralelo y deduplica resultados."""
        if not queries or not sources:
            return []

        # Asignar caché a fuentes que lo soporten
        for source in sources:
            if hasattr(source, "cache") and source.cache is None:
                source.cache = self.cache_repo

        results_by_source: list[SourceResult] = []
        seen_urls: set[str] = set()
        seen_dois: set[str] = set()
        seen_titles: set[str] = set()

        # Ejecutar consultas para todas las fuentes y queries
        tasks = []
        task_info = []

        for source in sources:
            for query in queries:
                tasks.append(self._search_source(source, query, limit))
                task_info.append((source.name, query))

        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for (source_name, query), result in zip(task_info, task_results, strict=False):
            start_time = time.monotonic()
            if isinstance(result, Exception):
                logger.warning("Fuente %s falló para query %r: %s", source_name, query, result)
                results_by_source.append(
                    SourceResult(
                        source=source_name,
                        resources=[],
                        error=str(result),
                        response_time_ms=0.0,
                    )
                )
                continue

            if isinstance(result, list):
                # Deduplicar recursos globalmente
                deduplicated_resources = []
                for resource in result:
                    if not isinstance(resource, Resource):
                        continue

                    url_key = _normalize_url_key(resource.url)
                    doi_key = resource.doi.lower().strip() if resource.doi else None
                    title_key = _normalize_title_key(resource.title)

                    is_duplicate = False
                    if url_key in seen_urls:
                        is_duplicate = True
                    elif doi_key and doi_key in seen_dois:
                        is_duplicate = True
                    elif title_key and title_key in seen_titles and len(title_key) > 10:
                        is_duplicate = True

                    if not is_duplicate:
                        seen_urls.add(url_key)
                        if doi_key:
                            seen_dois.add(doi_key)
                        if title_key:
                            seen_titles.add(title_key)
                        deduplicated_resources.append(resource)

                elapsed_ms = (time.monotonic() - start_time) * 1000
                results_by_source.append(
                    SourceResult(
                        source=source_name,
                        resources=deduplicated_resources,
                        error=None,
                        response_time_ms=elapsed_ms,
                    )
                )

        return results_by_source

    async def _search_source(self, source: Source, query: str, limit: int) -> list[Resource]:
        """Busca en una fuente específica."""
        try:
            if hasattr(source, "search"):
                resources = await source.search(query, limit)
                return resources if isinstance(resources, list) else []
        except Exception as exc:
            logger.debug("Error buscando en %s: %s", getattr(source, "name", source), exc)
            raise
        return []


__all__ = ["MultiSourceRetriever", "Retriever"]
