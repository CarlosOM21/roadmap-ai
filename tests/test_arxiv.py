"""Pruebas del conector de arXiv con XML simulado."""

from __future__ import annotations

import httpx
import pytest

from roadmap_ai.config import Settings
from roadmap_ai.models import ResourceType
from roadmap_ai.sources.arxiv import ArxivSource
from roadmap_ai.sources.errors import SourceParseError

ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <updated>2024-01-02T10:00:00Z</updated>
    <published>2024-01-01T10:00:00Z</published>
    <title>Control   systems
      para todos</title>
    <summary>Un resumen
      de prueba.</summary>
    <author><name>Ada Lovelace</name></author>
    <author><name>Grace Hopper</name></author>
    <link href="http://arxiv.org/abs/2401.00001v1"
          rel="alternate" type="text/html"/>
    <arxiv:primary_category term="cs.SY" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.SY" scheme="http://arxiv.org/schemas/atom"/>
    <category term="math.OC" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:doi>10.1234/ARXIV</arxiv:doi>
    <arxiv:journal_ref>Journal of Control 1 (2024)</arxiv:journal_ref>
  </entry>
</feed>
"""


async def test_arxiv_parses_atom_entry() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "export.arxiv.org"
        assert request.url.params["search_query"] == 'all:"control systems"'
        assert request.url.params["max_results"] == "1"
        return httpx.Response(200, text=ARXIV_XML)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = ArxivSource(
            Settings(_env_file=None, max_retries=0),
            client=client,
            min_interval=0,
        )
        resources = await source.search("control systems", limit=1)

    assert len(resources) == 1
    resource = resources[0]
    assert resource.type is ResourceType.PAPER
    assert resource.title == "Control systems para todos"
    assert resource.summary == "Un resumen de prueba."
    assert resource.authors == ["Ada Lovelace", "Grace Hopper"]
    assert resource.year == 2024
    assert resource.url == "https://arxiv.org/abs/2401.00001v1"
    assert resource.doi == "10.1234/arxiv"
    assert resource.open_access is True
    assert resource.raw_metadata["categories"] == ["cs.SY", "math.OC"]
    assert resource.raw_metadata["primary_category"] == "cs.SY"


async def test_arxiv_raises_parse_error_for_invalid_xml() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="<feed"))
    ) as client:
        source = ArxivSource(
            Settings(_env_file=None, max_retries=0),
            client=client,
            min_interval=0,
        )
        with pytest.raises(SourceParseError):
            await source.search("control")
