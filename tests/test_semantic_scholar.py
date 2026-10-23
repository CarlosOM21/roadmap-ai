"""Pruebas del conector de Semantic Scholar con respuestas simuladas."""

from __future__ import annotations

import httpx

from roadmap_ai.config import Settings
from roadmap_ai.models import ResourceType
from roadmap_ai.sources.semantic_scholar import SemanticScholarSource


async def test_semantic_scholar_uses_api_key_and_maps_paper() -> None:
    payload = {
        "data": [
            {
                "paperId": "paper-123",
                "title": "Aprendizaje profundo",
                "abstract": "Un resumen académico.",
                "year": 2022,
                "authors": [{"name": "Ada Lovelace"}, {"name": "Grace Hopper"}],
                "externalIds": {"DOI": "10.5555/TEST"},
                "url": "https://www.semanticscholar.org/paper/paper-123",
                "openAccessPdf": {"url": "https://example.org/paper.pdf"},
                "citationCount": 42,
                "fieldsOfStudy": ["Computer Science"],
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.semanticscholar.org"
        assert request.headers["x-api-key"] == "secret-key"
        assert request.url.params["limit"] == "1"
        assert "abstract" in request.url.params["fields"]
        return httpx.Response(200, json=payload)

    settings = Settings(_env_file=None, semantic_scholar_api_key="secret-key", max_retries=0)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = SemanticScholarSource(settings, client=client, min_interval=0)
        resources = await source.search("deep learning", limit=1)

    assert len(resources) == 1
    resource = resources[0]
    assert resource.type is ResourceType.PAPER
    assert resource.title == "Aprendizaje profundo"
    assert resource.authors == ["Ada Lovelace", "Grace Hopper"]
    assert resource.doi == "10.5555/test"
    assert resource.url == "https://example.org/paper.pdf"
    assert resource.open_access is True
    assert resource.citation_count == 42
    assert resource.raw_metadata["paper_id"] == "paper-123"


async def test_semantic_scholar_falls_back_to_doi_url() -> None:
    payload = {
        "data": [
            {
                "paperId": "paper-456",
                "title": "Paper cerrado",
                "externalIds": {"DOI": "10.5555/closed"},
                "url": None,
                "openAccessPdf": None,
            }
        ]
    }

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        source = SemanticScholarSource(
            Settings(_env_file=None, max_retries=0),
            client=client,
            min_interval=0,
        )
        resources = await source.search("closed paper")

    assert len(resources) == 1
    assert resources[0].url == "https://doi.org/10.5555/closed"
    assert resources[0].open_access is False
