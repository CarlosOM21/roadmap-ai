"""Pruebas de la CLI con Typer y una base de datos temporal."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from typer.testing import CliRunner

from roadmap_ai.cli import app
from roadmap_ai.config import get_settings
from roadmap_ai.storage import Database, RoadmapRepository

runner = CliRunner()


@pytest.fixture
def cli_database(tmp_path, monkeypatch) -> Iterator[str]:
    database_url = f"sqlite:///{tmp_path / 'cli.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    yield database_url
    get_settings.cache_clear()


def _repository(database_url: str) -> RoadmapRepository:
    database = Database(database_url)
    database.create_all()
    return RoadmapRepository(database)


def test_generate_saves_roadmap_and_writes_markdown(
    cli_database: str,
    tmp_path,
) -> None:
    output = tmp_path / "roadmap.md"

    result = runner.invoke(
        app,
        [
            "generate",
            "sistemas de control",
            "--depth",
            "5",
            "--max-resources",
            "8",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists()
    assert "# Roadmap: Sistemas de control" in output.read_text(encoding="utf-8")
    summaries = _repository(cli_database).list_summaries()
    assert len(summaries) == 1
    assert summaries[0].total_levels == 5


def test_list_show_progress_and_export_flow(cli_database: str, tmp_path) -> None:
    generate_result = runner.invoke(
        app,
        ["generate", "sistemas de control", "--max-resources", "8"],
    )
    assert generate_result.exit_code == 0, generate_result.output
    roadmap_id = _repository(cli_database).list_summaries()[0].id

    list_result = runner.invoke(app, ["list"])
    assert list_result.exit_code == 0, list_result.output
    assert "sistemas de" in list_result.output
    assert "control" in list_result.output
    assert "0/5" in list_result.output

    show_result = runner.invoke(app, ["show", roadmap_id[:8]])
    assert show_result.exit_code == 0, show_result.output
    assert "Nivel 1" in show_result.output

    progress_result = runner.invoke(
        app,
        ["progress", roadmap_id[:8], "--complete", "Nivel 1"],
    )
    assert progress_result.exit_code == 0, progress_result.output
    assert "Nivel 1 marcado como completado" in progress_result.output

    json_path = tmp_path / "roadmap.json"
    export_result = runner.invoke(
        app,
        [
            "export",
            roadmap_id[:8],
            "--format",
            "json",
            "--output",
            str(json_path),
        ],
    )
    assert export_result.exit_code == 0, export_result.output
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["completed_levels"] == [1]


def test_update_preserves_progress(cli_database: str) -> None:
    assert (
        runner.invoke(
            app,
            ["generate", "sistemas de control", "--max-resources", "8"],
        ).exit_code
        == 0
    )
    repository = _repository(cli_database)
    roadmap_id = repository.list_summaries()[0].id
    repository.set_level_completed(roadmap_id, 1)

    result = runner.invoke(app, ["update", roadmap_id[:8]])

    assert result.exit_code == 0, result.output
    assert repository.get_completed_levels(roadmap_id) == [1]


def test_show_reports_unknown_roadmap(cli_database: str) -> None:
    result = runner.invoke(app, ["show", "inexistente"])

    assert result.exit_code != 0
    assert "No existe" in result.output


def test_generate_rejects_empty_topic(cli_database: str) -> None:
    result = runner.invoke(app, ["generate", "   "])

    assert result.exit_code == 2
    assert "vacío" in result.output
