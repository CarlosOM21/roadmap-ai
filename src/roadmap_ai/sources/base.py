"""Interfaz y base común para los conectores de fuentes académicas."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

import httpx

from roadmap_ai.config import Settings, get_settings
from roadmap_ai.models import Resource
from roadmap_ai.sources.http import HttpClient, SleepFunction
from roadmap_ai.sources.utils import normalize_whitespace
from roadmap_ai.storage.repositories import SourceCacheRepository

logger = logging.getLogger(__name__)


@runtime_checkable
class Source(Protocol):
    """Contrato mínimo que debe cumplir cada conector legal.

    Los conectores devolverán únicamente recursos con URL verificable y no
    descargarán contenido protegido por derechos de autor.
    """

    name: str

    async def search(self, query: str, limit: int = 10) -> list[Resource]:
        """Busca recursos para una consulta y devuelve resultados normalizados."""
        ...


class BaseSource(ABC):
    """Base con caché, rate limiting y política HTTP común."""

    name = "base"
    display_name = "Base"
    min_interval = 0.0
    max_results = 100

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        cache: SourceCacheRepository | None = None,
        client: httpx.AsyncClient | None = None,
        sleep: SleepFunction = asyncio.sleep,
        min_interval: float | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache = cache
        self.http = HttpClient(
            source=self.display_name,
            timeout=self.settings.request_timeout,
            max_retries=self.settings.max_retries,
            user_agent=self._build_user_agent(),
            min_interval=self.min_interval if min_interval is None else min_interval,
            client=client,
            sleep=sleep,
        )

    @property
    def cache_enabled(self) -> bool:
        """Indica si esta fuente puede usar la caché persistente."""
        return self.cache is not None and self.settings.cache_ttl_seconds > 0

    def _build_user_agent(self) -> str:
        email = self.settings.openalex_email.strip()
        contact = f"; mailto:{email}" if email else ""
        return f"RoadmapAI/0.1 (academic roadmap CLI{contact})"

    async def search(self, query: str, limit: int = 10) -> list[Resource]:
        """Busca recursos, usando la caché cuando está disponible."""
        normalized_query = normalize_whitespace(query)
        if not normalized_query:
            return []

        effective_limit = max(1, min(limit, self.max_results))
        if self.cache_enabled:
            cached = self._cache_get(normalized_query, effective_limit)
            if cached is not None:
                logger.debug(
                    "%s: %d recursos desde caché para %r",
                    self.display_name,
                    len(cached),
                    normalized_query,
                )
                return cached

        resources = await self._search(normalized_query, effective_limit)

        if self.cache_enabled:
            self._cache_set(normalized_query, effective_limit, resources)
        return resources

    def _cache_get(self, query: str, limit: int) -> list[Resource] | None:
        if self.cache is None:
            return None
        try:
            return self.cache.get(self.name, query, limit)
        except Exception as exc:
            logger.warning(
                "%s: no se pudo leer la caché (%s); se consultará la API",
                self.display_name,
                type(exc).__name__,
            )
            return None

    def _cache_set(self, query: str, limit: int, resources: list[Resource]) -> None:
        if self.cache is None:
            return
        try:
            self.cache.set(
                self.name,
                query,
                limit,
                resources,
                self.settings.cache_ttl_seconds,
            )
        except Exception as exc:
            logger.warning(
                "%s: no se pudo guardar la caché (%s)",
                self.display_name,
                type(exc).__name__,
            )

    @abstractmethod
    async def _search(self, query: str, limit: int) -> list[Resource]:
        """Implementación específica de cada fuente."""

    async def aclose(self) -> None:
        """Libera el cliente HTTP interno."""
        await self.http.aclose()

    async def __aenter__(self) -> BaseSource:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()


__all__ = ["BaseSource", "Source"]
