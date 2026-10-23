"""Pruebas de persistencia SQLite y repositorios."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect

from roadmap_ai.models import Roadmap
from roadmap_ai.sample_data import build_sample_roadmap
from roadmap_ai.storage import (
    AmbiguousRoadmapIdError,
    Database,
    LevelNotFoundError,
    RoadmapNotFoundError,
    RoadmapRepository,
)


def test_schema_contains_required_tables(database: Database) -> None:
    tables = set(inspect(database.engine).get_table_names())

    assert {
        "topics",
        "roadmaps",
        "resources",
        "roadmap_levels",
        "roadmap_resources",
        "user_progress",
        "source_cache",
    } <= tables


def test_save_and_get_round_trip(database: Database, roadmap: Roadmap) -> None:
    repository = RoadmapRepository(database)

    repository.save(roadmap)
    restored = repository.get(roadmap.id)

    assert restored is not None
    assert restored.id == roadmap.id
    assert restored.topic == roadmap.topic
    assert restored.queries_used == roadmap.queries_used
    assert len(restored.levels) == len(roadmap.levels)
    assert {resource.id for resource in restored.resources} == {
        resource.id for resource in roadmap.resources
    }
    first_resource = restored.levels[0].resources[0]
    assert first_resource.url.startswith("https://")


def test_list_summaries_includes_counts(database: Database, roadmap: Roadmap) -> None:
    repository = RoadmapRepository(database)
    repository.save(roadmap)

    summaries = repository.list_summaries()

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.id == roadmap.id
    assert summary.total_levels == len(roadmap.levels)
    assert summary.resource_count == len(roadmap.resources)
    assert summary.progress_percent == 0


def test_progress_can_be_marked_and_unmarked(database: Database, roadmap: Roadmap) -> None:
    repository = RoadmapRepository(database)
    repository.save(roadmap)

    progress = repository.set_level_completed(roadmap.id, 1)
    assert progress.completed is True
    assert repository.get_completed_levels(roadmap.id) == [1]
    assert repository.list_summaries()[0].progress_percent == 20

    progress = repository.set_level_completed(roadmap.id, 1, completed=False)
    assert progress.completed is False
    assert progress.completed_at is None
    assert repository.get_completed_levels(roadmap.id) == []


def test_progress_requires_existing_level(database: Database, roadmap: Roadmap) -> None:
    repository = RoadmapRepository(database)
    repository.save(roadmap)

    with pytest.raises(LevelNotFoundError):
        repository.set_level_completed(roadmap.id, 99)


def test_save_update_preserves_progress(database: Database, roadmap: Roadmap) -> None:
    repository = RoadmapRepository(database)
    repository.save(roadmap)
    repository.set_level_completed(roadmap.id, 2)

    updated = build_sample_roadmap(
        roadmap.topic,
        depth=len(roadmap.levels),
        max_resources=len(roadmap.resources),
        roadmap_id=roadmap.id,
        created_at=roadmap.created_at,
    )
    repository.save(updated)

    assert repository.get_completed_levels(roadmap.id) == [2]
    assert repository.get(roadmap.id) is not None


def test_resolve_id_accepts_unique_prefix(database: Database, roadmap: Roadmap) -> None:
    repository = RoadmapRepository(database)
    repository.save(roadmap)

    assert repository.resolve_id(roadmap.id[:8]) == roadmap.id


def test_resolve_id_detects_ambiguous_prefix(database: Database) -> None:
    repository = RoadmapRepository(database)
    first = build_sample_roadmap(
        "control",
        roadmap_id="aaaaaaaa-1111-4111-8111-111111111111",
    )
    second = build_sample_roadmap(
        "control",
        roadmap_id="aaaaaaaa-2222-4222-8222-222222222222",
    )
    repository.save(first)
    repository.save(second)

    with pytest.raises(AmbiguousRoadmapIdError):
        repository.resolve_id("aaaaaaaa")


def test_missing_roadmap_raises(database: Database) -> None:
    repository = RoadmapRepository(database)

    with pytest.raises(RoadmapNotFoundError):
        repository.resolve_id("no-existe")
    assert repository.get("no-existe") is None
