"""Conector de YouTube Data API v3 para recursos audiovisuales."""

from __future__ import annotations

import html
import logging
import re
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

YOUTUBE_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


class YouTubeSource(BaseSource):
    """Fuente de videos educativos mediante YouTube Data API v3."""

    name = "youtube"
    display_name = "YouTube"
    min_interval = 0.2
    max_results = 25

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._warned_missing_key = False

    def _api_key(self) -> str:
        if self.settings.youtube_api_key is None:
            return ""
        return self.settings.youtube_api_key.get_secret_value().strip()

    @property
    def cache_enabled(self) -> bool:
        """YouTube no consulta ni cachea resultados sin API key."""
        return bool(self._api_key()) and super().cache_enabled

    async def _search(self, query: str, limit: int) -> list[Resource]:
        api_key = self._api_key()
        if not api_key:
            if not self._warned_missing_key:
                logger.warning(
                    "%s: YOUTUBE_API_KEY no está configurada; se omite esta fuente.",
                    self.display_name,
                )
                self._warned_missing_key = True
            return []

        params = {
            "part": "snippet",
            "q": f"{query} curso OR tutorial",
            "type": "video",
            "maxResults": limit,
            "order": "relevance",
            "relevanceLanguage": "es",
            "safeSearch": "strict",
            "key": api_key,
        }
        payload = await self.http.get_json(YOUTUBE_ENDPOINT, params=params)
        if not isinstance(payload, dict):
            raise SourceParseError(self.display_name, "la respuesta no es un objeto JSON")
        items = payload.get("items")
        if items is None:
            items = []
        if not isinstance(items, list):
            raise SourceParseError(self.display_name, "la respuesta no contiene una lista 'items'")

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
        item_id = item.get("id") or {}
        snippet = item.get("snippet") or {}
        if not isinstance(item_id, dict) or not isinstance(snippet, dict):
            return None

        video_id = item_id.get("videoId")
        if not isinstance(video_id, str) or not YOUTUBE_VIDEO_ID.fullmatch(video_id):
            return None

        title = normalize_whitespace(html.unescape(str(snippet.get("title") or "")))
        if not title:
            return None

        url = safe_http_url(f"https://www.youtube.com/watch?v={video_id}")
        if url is None:
            return None

        channel_title = normalize_whitespace(html.unescape(str(snippet.get("channelTitle") or "")))
        description = normalize_whitespace(html.unescape(str(snippet.get("description") or "")))
        published_at = snippet.get("publishedAt")
        thumbnail_url = None
        thumbnails = snippet.get("thumbnails") or {}
        if isinstance(thumbnails, dict):
            default_thumbnail = thumbnails.get("medium") or thumbnails.get("default") or {}
            if isinstance(default_thumbnail, dict):
                thumbnail_url = safe_http_url(default_thumbnail.get("url"))

        summary = truncate(description, max_chars=1500)
        if channel_title:
            summary = f"Canal: {channel_title}. {summary}".strip()

        try:
            return Resource(
                id=stable_resource_id(self.name, video_id),
                type=ResourceType.VIDEO,
                title=title,
                authors=[channel_title] if channel_title else [],
                year=year_from_iso(published_at),
                url=url,
                doi=None,
                source=self.display_name,
                summary=summary,
                open_access=True,
                citation_count=None,
                raw_metadata={
                    "video_id": video_id,
                    "channel_id": snippet.get("channelId"),
                    "channel_title": channel_title or None,
                    "published_at": published_at,
                    "thumbnail_url": thumbnail_url,
                },
            )
        except ValidationError:
            logger.debug("%s: metadatos inválidos descartados: %r", self.display_name, title)
            return None


__all__ = ["YouTubeSource"]
