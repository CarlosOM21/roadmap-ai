"""Conector de arXiv mediante su API Atom/XML oficial."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
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
    year_from_iso,
)

logger = logging.getLogger(__name__)

ARXIV_ENDPOINT = "https://export.arxiv.org/api/query"
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"
ATOM = f"{{{ATOM_NS}}}"
ARXIV = f"{{{ARXIV_NS}}}"


class ArxivSource(BaseSource):
    """Fuente de preprints y papers de acceso abierto mediante la API Atom."""

    name = "arxiv"
    display_name = "arXiv"
    min_interval = 2.0
    max_results = 50

    async def _search(self, query: str, limit: int) -> list[Resource]:
        safe_query = query.replace('"', " ").strip()
        params: dict[str, Any] = {
            "search_query": f'all:"{safe_query}"',
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        xml_text = await self.http.get_text(ARXIV_ENDPOINT, params=params)
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise SourceParseError(self.display_name, "XML inválido") from exc

        entries = root.findall(f"{ATOM}entry")
        resources: list[Resource] = []
        for entry in entries:
            resource = self._entry_to_resource(entry)
            if resource is not None:
                resources.append(resource)

        logger.info("%s: %d recursos para %r", self.display_name, len(resources), query)
        return resources

    def _entry_to_resource(self, entry: ET.Element) -> Resource | None:
        title = normalize_whitespace(entry.findtext(f"{ATOM}title"))
        if not title:
            return None

        abstract_url = None
        for link in entry.findall(f"{ATOM}link"):
            if link.attrib.get("rel") == "alternate":
                abstract_url = safe_http_url(link.attrib.get("href"))
                if abstract_url:
                    break
        if abstract_url is None:
            abstract_url = safe_http_url(entry.findtext(f"{ATOM}id"))
        if abstract_url is None:
            logger.debug("%s: recurso descartado sin URL: %r", self.display_name, title)
            return None
        abstract_url = abstract_url.replace("http://arxiv.org/", "https://arxiv.org/", 1)

        authors = []
        for author in entry.findall(f"{ATOM}author"):
            name = normalize_whitespace(author.findtext(f"{ATOM}name"))
            if name:
                authors.append(name)

        categories = [
            category.attrib["term"]
            for category in entry.findall(f"{ATOM}category")
            if category.attrib.get("term")
        ]
        primary_category = entry.find(f"{ARXIV}primary_category")
        primary_term = primary_category.attrib.get("term") if primary_category is not None else None
        doi = normalize_whitespace(entry.findtext(f"{ARXIV}doi")) or None
        published = entry.findtext(f"{ATOM}published")
        updated = entry.findtext(f"{ATOM}updated")
        arxiv_id = normalize_whitespace(entry.findtext(f"{ATOM}id")) or abstract_url
        journal_ref = normalize_whitespace(entry.findtext(f"{ARXIV}journal_ref")) or None

        try:
            return Resource(
                id=stable_resource_id(self.name, arxiv_id),
                type=ResourceType.PAPER,
                title=title,
                authors=authors,
                year=year_from_iso(published),
                url=abstract_url,
                doi=doi,
                source=self.display_name,
                summary=truncate(entry.findtext(f"{ATOM}summary"), max_chars=2500),
                open_access=True,
                citation_count=None,
                raw_metadata={
                    "arxiv_id": arxiv_id,
                    "categories": categories,
                    "primary_category": primary_term,
                    "published": published,
                    "updated": updated,
                    "journal_ref": journal_ref,
                },
            )
        except ValidationError:
            logger.debug("%s: metadatos inválidos descartados: %r", self.display_name, title)
            return None


__all__ = ["ArxivSource"]
