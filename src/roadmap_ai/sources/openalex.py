"""Conector de OpenAlex para trabajos académicos de acceso abierto."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from roadmap_ai.models import Resource, ResourceType
from roadmap_ai.sources.base import BaseSource
from roadmap_ai.sources.errors import SourceParseError
from roadmap_ai.sources.utils import (
    doi_url,
    normalize_whitespace,
    safe_http_url,
    stable_resource_id,
    truncate,
    year_from_iso,
)

logger = logging.getLogger(__name__)

OPENALEX_ENDPOINT = "https://api.openalex.org/works"
OPENALEX_SELECT = ",".join(
    [
        "id",
        "doi",
        "title",
        "display_name",
        "publication_year",
        "type",
        "authorships",
        "abstract_inverted_index",
        "primary_location",
        "best_oa_location",
        "open_access",
        "cited_by_count",
    ]
)


class OpenAlexSource(BaseSource):
    """Fuente de papers y trabajos académicos mediante la API de OpenAlex."""

    name = "openalex"
    display_name = "OpenAlex"
    min_interval = 0.5
    max_results = 50

    async def _search(self, query: str, limit: int) -> list[Resource]:
        params: dict[str, Any] = {
            "search": query,
            "filter": "open_access.is_oa:true",
            "per-page": limit,
            "select": OPENALEX_SELECT,
        }
        if self.settings.openalex_email.strip():
            params["mailto"] = self.settings.openalex_email.strip()

        payload = await self.http.get_json(OPENALEX_ENDPOINT, params=params)
        if not isinstance(payload, dict):
            raise SourceParseError(self.display_name, "la respuesta no es un objeto JSON")
        works = payload.get("results")
        if not isinstance(works, list):
            raise SourceParseError(self.display_name, "la respuesta no contiene 'results'")

        resources: list[Resource] = []
        for work in works:
            if not isinstance(work, dict):
                continue
            resource = self._work_to_resource(work)
            if resource is not None:
                resources.append(resource)
        logger.info("%s: %d recursos para %r", self.display_name, len(resources), query)
        return resources

    def _work_to_resource(self, work: dict[str, Any]) -> Resource | None:
        title = normalize_whitespace(work.get("title") or work.get("display_name"))
        if not title:
            return None

        doi_raw = work.get("doi")
        best_location = work.get("best_oa_location") or {}
        primary_location = work.get("primary_location") or {}
        if not isinstance(best_location, dict):
            best_location = {}
        if not isinstance(primary_location, dict):
            primary_location = {}

        url_candidates = [
            safe_http_url(best_location.get("landing_page_url")),
            safe_http_url(best_location.get("pdf_url")),
            safe_http_url(primary_location.get("landing_page_url")),
            safe_http_url(primary_location.get("pdf_url")),
        ]
        if isinstance(doi_raw, str) and doi_raw.strip():
            url_candidates.append(safe_http_url(doi_raw) or doi_url(doi_raw))
        url = next((candidate for candidate in url_candidates if candidate), None)
        if url is None:
            logger.debug("%s: recurso descartado sin URL verificable: %r", self.display_name, title)
            return None

        authors = []
        for authorship in work.get("authorships") or []:
            if not isinstance(authorship, dict):
                continue
            author = authorship.get("author") or {}
            if isinstance(author, dict):
                name = normalize_whitespace(author.get("display_name"))
                if name:
                    authors.append(name)

        open_access_data = work.get("open_access") or {}
        if not isinstance(open_access_data, dict):
            open_access_data = {}
        open_access = bool(open_access_data.get("is_oa")) or any(
            candidate is not None
            for candidate in (
                safe_http_url(best_location.get("landing_page_url")),
                safe_http_url(best_location.get("pdf_url")),
            )
        )

        raw_type = normalize_whitespace(str(work.get("type") or "")).lower()
        resource_type = ResourceType.BOOK if raw_type == "book" else ResourceType.PAPER
        citation_count = work.get("cited_by_count")
        if not isinstance(citation_count, int) or citation_count < 0:
            citation_count = None

        openalex_id = work.get("id")
        identifier = str(openalex_id or doi_raw or url)
        raw_metadata = {
            "openalex_id": openalex_id,
            "type": raw_type or None,
            "oa_status": open_access_data.get("oa_status"),
            "best_oa_landing_page_url": safe_http_url(best_location.get("landing_page_url")),
            "best_oa_pdf_url": safe_http_url(best_location.get("pdf_url")),
        }

        try:
            return Resource(
                id=stable_resource_id(self.name, identifier),
                type=resource_type,
                title=title,
                authors=authors,
                year=year_from_iso(work.get("publication_year")),
                url=url,
                doi=doi_raw if isinstance(doi_raw, str) else None,
                source=self.display_name,
                summary=truncate(self._reconstruct_abstract(work.get("abstract_inverted_index"))),
                open_access=open_access,
                citation_count=citation_count,
                raw_metadata=raw_metadata,
            )
        except ValidationError:
            logger.debug("%s: metadatos inválidos descartados: %r", self.display_name, title)
            return None

    @staticmethod
    def _reconstruct_abstract(inverted_index: object) -> str:
        """Convierte ``abstract_inverted_index`` en texto legible."""
        if not isinstance(inverted_index, dict):
            return ""

        positioned_words: dict[int, str] = {}
        for word, positions in inverted_index.items():
            if not isinstance(word, str) or not isinstance(positions, list):
                continue
            for position in positions:
                if isinstance(position, int):
                    positioned_words[position] = word
        return " ".join(positioned_words[position] for position in sorted(positioned_words))


__all__ = ["OpenAlexSource"]
