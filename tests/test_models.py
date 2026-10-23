"""Pruebas de los modelos de dominio."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from roadmap_ai.models import (
    Resource,
    ResourceType,
    Roadmap,
    RoadmapLevel,
    SourceResult,
    Topic,
    slugify,
)
from roadmap_ai.sample_data import build_sample_roadmap


def test_slugify_handles_accents_and_spaces() -> None:
    assert slugify("Sistemas de Control") == "sistemas-de-control"
    assert slugify("Procesamiento de imágenes") == "procesamiento-de-imagenes"


def test_topic_generates_slug_and_timestamp() -> None:
    topic = Topic(name="Redes Neuronales")

    assert topic.id
    assert topic.slug == "redes-neuronales"
    assert topic.created_at.tzinfo is not None


def test_topic_rejects_invalid_slug() -> None:
    with pytest.raises(ValidationError):
        Topic(name="Control", slug="Slug Inválido")


def test_resource_normalizes_doi() -> None:
    resource = Resource(
        type=ResourceType.PAPER,
        title="A paper",
        url="https://example.org/paper",
        doi="https://doi.org/10.1000/ABC123",
        source="OpenAlex",
    )

    assert resource.doi == "10.1000/abc123"


def test_resource_rejects_non_http_url() -> None:
    with pytest.raises(ValidationError):
        Resource(
            type=ResourceType.PAPER,
            title="Invalid",
            url="ftp://example.org/file.pdf",
            source="Unknown",
        )


def test_resource_validates_relevance_score() -> None:
    with pytest.raises(ValidationError):
        Resource(
            type=ResourceType.PAPER,
            title="Invalid score",
            url="https://example.org/paper",
            source="Unknown",
            relevance_score=1.5,
        )


def test_resource_cleans_duplicate_authors() -> None:
    resource = Resource(
        type=ResourceType.BOOK,
        title="Book",
        authors=[" Ada Lovelace ", "ada lovelace", "Grace Hopper"],
        url="https://example.org/book",
        source="Open Library",
    )

    assert resource.authors == ["Ada Lovelace", "Grace Hopper"]


def test_roadmap_aggregates_level_resources() -> None:
    roadmap = build_sample_roadmap("sistemas de control", depth=4, max_resources=20)
    level_resource_ids = {resource.id for level in roadmap.levels for resource in level.resources}

    assert {resource.id for resource in roadmap.resources} == level_resource_ids
    assert len(roadmap.levels) == 4


def test_roadmap_rejects_duplicate_level_numbers() -> None:
    resource = Resource(
        type=ResourceType.TOOL,
        title="Tool",
        url="https://example.org/tool",
        source="Example",
    )
    level = RoadmapLevel(number=1, title="Uno", resources=[resource])

    with pytest.raises(ValidationError):
        Roadmap(
            topic="tema",
            title="Roadmap",
            levels=[level, level],
        )


def test_source_result_success_property() -> None:
    assert SourceResult(source="openalex", response_time_ms=12.5).success is True
    assert SourceResult(source="arxiv", error="HTTP 500").success is False


def test_sample_roadmap_resources_have_verifiable_urls() -> None:
    roadmap = build_sample_roadmap("sistemas de control", depth=6, max_resources=30)

    assert roadmap.resources
    assert all(resource.url.startswith(("http://", "https://")) for resource in roadmap.resources)
    assert all(resource.raw_metadata.get("demo") is True for resource in roadmap.resources)


def test_roadmap_json_round_trip() -> None:
    roadmap = build_sample_roadmap("control", depth=4, max_resources=5)

    restored = Roadmap.model_validate_json(roadmap.model_dump_json())

    assert restored.id == roadmap.id
    assert restored.topic == roadmap.topic
    assert len(restored.levels) == len(roadmap.levels)
