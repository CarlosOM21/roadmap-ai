"""Conector de GitHub API para repositorios educativos y herramientas."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from roadmap_ai.models import Resource, ResourceType
from roadmap_ai.sources.base import BaseSource
from roadmap_ai.sources.errors import SourceParseError
from roadmap_ai.sources.utils import (
    normalize_whitespace,
    safe_http_url,
    stable_resource_id,
    truncate,
)

logger = logging.getLogger(__name__)

GITHUB_SEARCH_ENDPOINT = "https://api.github.com/search/repositories"


class GitHubSource(BaseSource):
    """Fuente de repositorios GitHub educativos, ejemplos y herramientas."""

    name = "github"
    display_name = "GitHub"
    min_interval = 0.3
    max_results = 50

    async def _search(self, query: str, limit: int) -> list[Resource]:
        # Añadir términos para priorizar contenido educativo
        q = f"{query} stars:>10"
        params = {
            "q": q,
            "sort": "stars",
            "order": "desc",
            "per_page": min(limit, 50),
        }
        headers = {
            "Accept": "application/vnd.github+json",
        }
        # GitHub recomienda User-Agent; BaseSource ya lo añade
        payload = await self.http.get_json(GITHUB_SEARCH_ENDPOINT, params=params, headers=headers)
        if not isinstance(payload, dict):
            raise SourceParseError(self.display_name, "la respuesta no es un objeto JSON")
        items = payload.get("items")
        if not isinstance(items, list):
            raise SourceParseError(self.display_name, "la respuesta no contiene 'items'")

        resources: list[Resource] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            resource = self._item_to_resource(item)
            if resource is not None:
                resources.append(resource)

        logger.info("%s: %d recursos para %r", self.display_name, len(resources), query)
        return resources

    def _item_to_resource(self, item: dict[str, Any]) -> Resource | None:
        full_name = item.get("full_name")
        html_url = item.get("html_url")
        if not isinstance(full_name, str) or not full_name.strip():
            return None
        if not isinstance(html_url, str):
            return None

        url = safe_http_url(html_url)
        if url is None:
            return None

        title = normalize_whitespace(f"{full_name}: {item.get('description') or full_name}")
        description = normalize_whitespace(str(item.get("description") or ""))
        language = normalize_whitespace(str(item.get("language") or ""))
        topics = item.get("topics") or []
        if not isinstance(topics, list):
            topics = []

        summary_parts = []
        if description:
            summary_parts.append(description)
        if language:
            summary_parts.append(f"Lenguaje: {language}")
        if topics:
            summary_parts.append(
                f"Temas: {', '.join([t for t in topics if isinstance(t, str)][:8])}"
            )
        stars = item.get("stargazers_count")
        if isinstance(stars, int):
            summary_parts.append(f"Estrellas: {stars}")
        summary = truncate(". ".join(summary_parts), max_chars=1500)

        try:
            return Resource(
                id=stable_resource_id(self.name, full_name.lower()),
                type=ResourceType.TOOL,
                title=truncate(f"GitHub: {full_name}", max_chars=200),
                authors=[],
                year=None,
                url=url,
                doi=None,
                source=self.display_name,
                summary=summary,
                open_access=True,
                citation_count=None if not isinstance(stars, int) else stars,
                raw_metadata={
                    "full_name": full_name,
                    "language": language or None,
                    "topics": topics,
                    "stars": stars if isinstance(stars, int) else None,
                },
            )
        except ValidationError:
            logger.debug("%s: metadatos inválidos descartados: %r", self.display_name, full_name)
            return None


__all__ = ["GitHubSource"]
