"""Pruebas del conector de YouTube con respuestas simuladas."""

from __future__ import annotations

import httpx

from roadmap_ai.config import Settings
from roadmap_ai.models import ResourceType
from roadmap_ai.sources.youtube import YouTubeSource


async def test_youtube_without_key_returns_empty_without_request() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("No debería realizarse ninguna petición sin API key")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = YouTubeSource(
            Settings(_env_file=None, max_retries=0),
            client=client,
            min_interval=0,
        )
        resources = await source.search("control systems")

    assert resources == []
    assert source.cache_enabled is False


async def test_youtube_maps_video() -> None:
    payload = {
        "items": [
            {
                "id": {"kind": "youtube#video", "videoId": "dQw4w9WgXcQ"},
                "snippet": {
                    "title": "Curso de control &amp; sistemas",
                    "description": "Introducción   práctica.",
                    "channelId": "channel-1",
                    "channelTitle": "Academia",
                    "publishedAt": "2023-05-01T10:00:00Z",
                    "thumbnails": {
                        "medium": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg"}
                    },
                },
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.googleapis.com"
        assert request.url.params["key"] == "youtube-secret"
        assert "curso" in request.url.params["q"]
        assert request.url.params["maxResults"] == "1"
        return httpx.Response(200, json=payload)

    settings = Settings(_env_file=None, youtube_api_key="youtube-secret", max_retries=0)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = YouTubeSource(settings, client=client, min_interval=0)
        resources = await source.search("control systems", limit=1)

    assert len(resources) == 1
    resource = resources[0]
    assert resource.type is ResourceType.VIDEO
    assert resource.title == "Curso de control & sistemas"
    assert resource.authors == ["Academia"]
    assert resource.year == 2023
    assert resource.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert resource.summary == "Canal: Academia. Introducción práctica."
    assert resource.open_access is True
    assert resource.raw_metadata["video_id"] == "dQw4w9WgXcQ"


async def test_youtube_discards_invalid_video_id() -> None:
    payload = {"items": [{"id": {"videoId": "no-válido"}, "snippet": {"title": "X"}}]}

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        source = YouTubeSource(
            Settings(_env_file=None, youtube_api_key="key", max_retries=0),
            client=client,
            min_interval=0,
        )
        resources = await source.search("control")

    assert resources == []
