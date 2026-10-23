"""Pruebas de caché, reintentos y contrato base de las fuentes."""

from __future__ import annotations

import httpx
import pytest

from roadmap_ai.config import Settings
from roadmap_ai.models import Resource, ResourceType
from roadmap_ai.sources.base import BaseSource
from roadmap_ai.sources.errors import SourceHTTPError, SourceNetworkError, SourceParseError
from roadmap_ai.sources.http import HttpClient
from roadmap_ai.storage import Database, SourceCacheRepository


class CountingSource(BaseSource):
    """Fuente mínima que cuenta cuántas veces se consulta."""

    name = "counting"
    display_name = "Counting"
    max_results = 50

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.calls = 0

    async def _search(self, query: str, limit: int) -> list[Resource]:
        self.calls += 1
        return [
            Resource(
                type=ResourceType.PAPER,
                title=f"{query} ({limit})",
                url="https://example.org/paper",
                source=self.display_name,
                open_access=True,
            )
        ]


async def test_base_source_uses_cache(database: Database) -> None:
    repository = SourceCacheRepository(database)
    settings = Settings(_env_file=None, cache_ttl_seconds=3600, max_retries=0)

    async with httpx.AsyncClient() as client:
        source = CountingSource(
            settings,
            cache=repository,
            client=client,
            min_interval=0,
        )
        first = await source.search("Control Systems", limit=10)
        second = await source.search("  control   systems  ", limit=10)

    assert source.calls == 1
    assert [resource.id for resource in first] == [resource.id for resource in second]
    cached = repository.get("counting", "control systems", 10)
    assert cached is not None
    assert cached[0].title == "Control Systems (10)"


async def test_base_source_without_cache_calls_again(database: Database) -> None:
    repository = SourceCacheRepository(database)
    settings = Settings(_env_file=None, cache_ttl_seconds=0, max_retries=0)

    async with httpx.AsyncClient() as client:
        source = CountingSource(settings, cache=repository, client=client, min_interval=0)
        await source.search("tema")
        await source.search("tema")

    assert source.calls == 2
    assert source.cache_enabled is False
    assert repository.get("counting", "tema", 10) is None


async def test_source_cache_repository_round_trip_and_clear(database: Database) -> None:
    repository = SourceCacheRepository(database)
    resources = [
        Resource(
            type=ResourceType.BOOK,
            title="Libro",
            url="https://example.org/book",
            source="Test",
        )
    ]

    repository.set("test", "consulta", 5, resources, ttl_seconds=3600)
    restored = repository.get("test", "CONSULTA", 5)

    assert restored is not None
    assert restored[0].title == "Libro"
    assert repository.clear("otra") == 0
    assert repository.clear("test") == 1
    assert repository.get("test", "consulta", 5) is None


async def test_http_client_retries_429_then_succeeds() -> None:
    calls = 0
    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = HttpClient(
            source="test",
            timeout=1,
            max_retries=2,
            user_agent="RoadmapAI-test",
            min_interval=0,
            client=client,
            sleep=fake_sleep,
        )
        payload = await http.get_json("https://example.org/data")

    assert payload == {"ok": True}
    assert calls == 2
    assert delays == [0.0]


async def test_http_client_raises_after_retries() -> None:
    async def fake_sleep(_: float) -> None:
        return None

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = HttpClient(
            source="test",
            timeout=1,
            max_retries=1,
            user_agent="RoadmapAI-test",
            min_interval=0,
            client=client,
            sleep=fake_sleep,
            backoff_base=0.01,
        )
        with pytest.raises(SourceNetworkError):
            await http.get_json("https://example.org/data")


async def test_http_client_does_not_retry_400_or_invalid_json() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(400))
    ) as client:
        http = HttpClient(
            source="test",
            timeout=1,
            max_retries=3,
            user_agent="RoadmapAI-test",
            client=client,
        )
        with pytest.raises(SourceHTTPError) as exc_info:
            await http.get_json("https://example.org/data")
        assert exc_info.value.status_code == 400

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="no-json"))
    ) as client:
        http = HttpClient(
            source="test",
            timeout=1,
            max_retries=0,
            user_agent="RoadmapAI-test",
            client=client,
        )
        with pytest.raises(SourceParseError):
            await http.get_json("https://example.org/data")
