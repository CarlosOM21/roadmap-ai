"""Pruebas del conector de Open Library con respuestas simuladas."""

from __future__ import annotations

import httpx

from roadmap_ai.config import Settings
from roadmap_ai.models import ResourceType
from roadmap_ai.sources.open_library import OpenLibrarySource


async def test_open_library_maps_book() -> None:
    payload = {
        "docs": [
            {
                "key": "/works/OL123W",
                "title": "  Control   Systems  ",
                "author_name": ["Ada Lovelace", "Ada Lovelace"],
                "first_publish_year": 1999,
                "subject": ["Control", "Ingeniería", "Control"],
                "edition_count": 4,
                "ebook_access": "public",
                "ia": ["control00test"],
                "cover_i": 12345,
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "openlibrary.org"
        assert request.url.params["q"] == "control systems"
        assert request.url.params["limit"] == "2"
        assert "ebook_access" in request.url.params["fields"]
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = OpenLibrarySource(
            Settings(_env_file=None, max_retries=0),
            client=client,
            min_interval=0,
        )
        resources = await source.search("control systems", limit=2)

    assert len(resources) == 1
    resource = resources[0]
    assert resource.type is ResourceType.BOOK
    assert resource.title == "Control Systems"
    assert resource.authors == ["Ada Lovelace"]
    assert resource.year == 1999
    assert resource.url == "https://openlibrary.org/works/OL123W"
    assert resource.open_access is True
    assert resource.source == "Open Library"
    assert resource.summary.startswith("Temas: Control, Ingeniería")
    assert resource.raw_metadata["edition_count"] == 4
    assert resource.raw_metadata["ia_ids"] == ["control00test"]
    assert resource.raw_metadata["cover_url"].endswith("/12345-M.jpg")


async def test_open_library_borrowable_is_not_open_access() -> None:
    payload = {
        "docs": [
            {
                "key": "/works/OL456W",
                "title": "Libro prestado",
                "ebook_access": "borrowable",
            }
        ]
    }

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        source = OpenLibrarySource(
            Settings(_env_file=None, max_retries=0),
            client=client,
            min_interval=0,
        )
        resources = await source.search("libro")

    assert len(resources) == 1
    assert resources[0].open_access is False
    assert resources[0].url == "https://openlibrary.org/works/OL456W"
