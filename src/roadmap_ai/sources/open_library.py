"""Conector de Open Library para libros y metadatos bibliográficos."""

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
    year_from_iso,
)

logger = logging.getLogger(__name__)

OPEN_LIBRARY_ENDPOINT = "https://openlibrary.org/search.json"
OPEN_LIBRARY_FIELDS = ",".join(
    [
        "key",
        "title",
        "author_name",
        "first_publish_year",
        "subject",
        "edition_count",
        "ebook_access",
        "ia",
        "cover_i",
    ]
)


class OpenLibrarySource(BaseSource):
    """Fuente de libros y metadatos bibliográficos de Open Library."""

    name = "open_library"
    display_name = "Open Library"
    min_interval = 0.5
    max_results = 100

    async def _search(self, query: str, limit: int) -> list[Resource]:
        params = {
            "q": query,
            "limit": limit,
            "fields": OPEN_LIBRARY_FIELDS,
        }
        payload = await self.http.get_json(OPEN_LIBRARY_ENDPOINT, params=params)
        if not isinstance(payload, dict):
            raise SourceParseError(self.display_name, "la respuesta no es un objeto JSON")
        docs = payload.get("docs")
        if not isinstance(docs, list):
            raise SourceParseError(self.display_name, "la respuesta no contiene 'docs'")

        resources: list[Resource] = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            resource = self._doc_to_resource(doc)
            if resource is not None:
                resources.append(resource)

        logger.info("%s: %d recursos para %r", self.display_name, len(resources), query)
        return resources

    def _doc_to_resource(self, doc: dict[str, Any]) -> Resource | None:
        title = normalize_whitespace(doc.get("title"))
        key = doc.get("key")
        if not title or not isinstance(key, str) or not key.strip():
            return None

        key = key.strip()
        if key.startswith(("http://", "https://")):
            url = safe_http_url(key)
        else:
            url = safe_http_url(f"https://openlibrary.org/{key.lstrip('/')}")
        if url is None:
            logger.debug("%s: recurso descartado sin URL: %r", self.display_name, title)
            return None

        authors = []
        for author in doc.get("author_name") or []:
            if isinstance(author, str):
                name = normalize_whitespace(author)
                if name:
                    authors.append(name)

        subjects = [
            normalize_whitespace(subject)
            for subject in (doc.get("subject") or [])
            if isinstance(subject, str) and subject.strip()
        ]
        ebook_access = normalize_whitespace(str(doc.get("ebook_access") or "")).lower()
        open_access = ebook_access == "public"
        cover_id = doc.get("cover_i")
        cover_url = (
            f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
            if isinstance(cover_id, int)
            else None
        )
        edition_count = doc.get("edition_count")
        if not isinstance(edition_count, int) or edition_count < 0:
            edition_count = None
        ia_ids = [item for item in (doc.get("ia") or []) if isinstance(item, str)]

        summary = f"Temas: {truncate(', '.join(subjects[:8]), max_chars=500)}" if subjects else ""

        try:
            return Resource(
                id=stable_resource_id(self.name, key),
                type=ResourceType.BOOK,
                title=title,
                authors=authors,
                year=year_from_iso(doc.get("first_publish_year")),
                url=url,
                doi=None,
                source=self.display_name,
                summary=summary,
                open_access=open_access,
                citation_count=None,
                raw_metadata={
                    "work_key": key,
                    "edition_count": edition_count,
                    "ebook_access": ebook_access or None,
                    "subjects": subjects[:20],
                    "ia_ids": ia_ids[:10],
                    "cover_url": cover_url,
                },
            )
        except ValidationError:
            logger.debug("%s: metadatos inválidos descartados: %r", self.display_name, title)
            return None


__all__ = ["OpenLibrarySource"]
