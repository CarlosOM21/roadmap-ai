"""Pruebas del conector de OpenAlex con respuestas simuladas."""

from __future__ import annotations

import httpx

from roadmap_ai.config import Settings
from roadmap_ai.models import ResourceType
from roadmap_ai.sources.openalex import OpenAlexSource


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


async def test_openalex_maps_open_access_work() -> None:
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "doi": "https://doi.org/10.1234/ABC",
                "title": "  Control   Systems  ",
                "publication_year": 2020,
                "type": "article",
                "authorships": [
                    {"author": {"display_name": "Ada Lovelace"}},
                    {"author": {"display_name": "Ada Lovelace"}},
                    {"author": {"display_name": "Grace Hopper"}},
                ],
                "abstract_inverted_index": {
                    "Control": [0],
                    "systems": [1],
                    "matter": [2],
                },
                "best_oa_location": {
                    "landing_page_url": "https://example.org/paper",
                    "pdf_url": "http://example.org/paper.pdf",
                },
                "primary_location": {"landing_page_url": "https://publisher.example/paper"},
                "open_access": {"is_oa": True, "oa_status": "gold"},
                "cited_by_count": 12,
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.openalex.org"
        assert request.url.params["filter"] == "open_access.is_oa:true"
        assert request.url.params["per-page"] == "2"
        assert request.url.params["mailto"] == "test@example.com"
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = OpenAlexSource(
            _settings(openalex_email="test@example.com", max_retries=0),
            client=client,
            min_interval=0,
        )
        resources = await source.search("control systems", limit=2)

    assert len(resources) == 1
    resource = resources[0]
    assert resource.type is ResourceType.PAPER
    assert resource.title == "Control Systems"
    assert resource.authors == ["Ada Lovelace", "Grace Hopper"]
    assert resource.year == 2020
    assert resource.doi == "10.1234/abc"
    assert resource.url == "https://example.org/paper"
    assert resource.open_access is True
    assert resource.citation_count == 12
    assert resource.summary == "Control systems matter"
    assert resource.source == "OpenAlex"
    assert resource.raw_metadata["oa_status"] == "gold"


async def test_openalex_discards_work_without_url() -> None:
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W999",
                "title": "Sin ubicación abierta",
                "publication_year": 2021,
                "best_oa_location": None,
                "primary_location": None,
            }
        ]
    }

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = OpenAlexSource(_settings(max_retries=0), client=client, min_interval=0)
        resources = await source.search("sin url")

    assert resources == []


def test_reconstruct_abstract_ignores_invalid_positions() -> None:
    inverted = {
        "Uno": [0, "malo"],
        "dos": [1],
        "ignorada": "no-es-lista",
    }

    assert OpenAlexSource._reconstruct_abstract(inverted) == "Uno dos"
    assert OpenAlexSource._reconstruct_abstract(None) == ""
