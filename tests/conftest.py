"""Fixtures compartidas por las pruebas."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from roadmap_ai.models import Roadmap
from roadmap_ai.sample_data import build_sample_roadmap
from roadmap_ai.storage import Database


@pytest.fixture
def database(tmp_path) -> Iterator[Database]:
    db = Database(f"sqlite:///{tmp_path / 'test.db'}")
    db.create_all()
    yield db
    db.dispose()


@pytest.fixture
def roadmap() -> Roadmap:
    return build_sample_roadmap("sistemas de control", depth=5, max_resources=20)
