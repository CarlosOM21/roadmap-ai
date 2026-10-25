"""Conector de Semantic Scholar Graph API."""

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

SEMANTIC_SCHOLAR_ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = ",".join(
    [
        "title",
        "abstract",
        "year",
        "authors",
        "externalIds",
        "url",
        "openAccessPdf",
        "citationCount",
        "fieldsOfStudy",
    ]
)


class SemanticScholarSource(BaseSource):
    """Fuente de papers mediante Semantic Scholar Graph API."""

    name = "semantic_scholar"
    display_name = "Semantic Scholar"
    min_interval = 1.5
    max_results = 50

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._warned_public_mode = False

    def _api_key(self) -> str:
        if self.settings.semantic_scholar_api_key is None:
            return ""
        return self.settings.semantic_scholar_api_key.get_secret_value().strip()

    async def _search(self, query: str, limit: int) -> list[Resource]:
        api_key = self._api_key()
        if not api_key and not self._warned_public_mode:
            logger.warning(
                "%s: sin API key; se usarán los límites públicos. "
                "Configura SEMANTIC_SCHOLAR_API_KEY para mayor estabilidad.",
                self.display_name,
            )
            self._warned_public_mode = True

        headers = {"x-api-key": api_key} if api_key else None
        params = {
            "query": query,
            "limit": limit,
            "fields": SEMANTIC_SCHOLAR_FIELDS,
        }
        payload = await self.http.get_json(
            SEMANTIC_SCHOLAR_ENDPOINT,
            params=params,
            headers=headers,
        )
        if not isinstance(payload, dict):
            raise SourceParseError(self.display_name, "la respuesta no es un objeto JSON")
        papers = payload.get("data")
        if papers is None:
            papers = []
        if not isinstance(papers, list):
            raise SourceParseError(self.display_name, "la respuesta no contiene una lista 'data'")

        resources: list[Resource] = []
        for paper in papers:
            if not isinstance(paper, dict):
                continue
            resource = self._paper_to_resource(paper)
            if resource is not None:
                resources.append(resource)
        logger.info("%s: %d recursos para %r", self.display_name, len(resources), query)
        return resources

    def _paper_to_resource(self, paper: dict[str, Any]) -> Resource | None:
        title = normalize_whitespace(paper.get("title"))
        if not title:
            return None

        external_ids = paper.get("externalIds") or {}
        if not isinstance(external_ids, dict):
            external_ids = {}
        doi = external_ids.get("DOI")
        doi = doi.strip() if isinstance(doi, str) and doi.strip() else None

        open_access_pdf = paper.get("openAccessPdf") or {}
        if not isinstance(open_access_pdf, dict):
            open_access_pdf = {}
        pdf_url = safe_http_url(open_access_pdf.get("url"))
        paper_url = safe_http_url(paper.get("url"))
        url = pdf_url or paper_url or (doi_url(doi) if doi else None)
        if url is None:
            logger.debug("%s: recurso descartado sin URL verificable: %r", self.display_name, title)
            return None

        authors = []
        for author in paper.get("authors") or []:
            if not isinstance(author, dict):
                continue
            name = normalize_whitespace(author.get("name"))
            if name:
                authors.append(name)

        citation_count = paper.get("citationCount")
        if not isinstance(citation_count, int) or citation_count < 0:
            citation_count = None

        paper_id = paper.get("paperId")
        identifier = str(paper_id or doi or url)
        fields_of_study = paper.get("fieldsOfStudy") or []
        raw_metadata = {
            "paper_id": paper_id,
            "external_ids": external_ids,
            "fields_of_study": fields_of_study if isinstance(fields_of_study, list) else [],
            "open_access_pdf_url": pdf_url,
        }

        try:
            return Resource(
                id=stable_resource_id(self.name, identifier),
                type=ResourceType.PAPER,
                title=title,
                authors=authors,
                year=year_from_iso(paper.get("year")),
                url=url,
                doi=doi,
                source=self.display_name,
                summary=truncate(paper.get("abstract")),
                open_access=pdf_url is not None,
                citation_count=citation_count,
                raw_metadata=raw_metadata,
            )
        except ValidationError:
            logger.debug("%s: metadatos inválidos descartados: %r", self.display_name, title)
            return None


__all__ = ["SemanticScholarSource"]
