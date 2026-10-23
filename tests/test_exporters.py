"""Pruebas de exportación a Markdown y JSON."""

from __future__ import annotations

import json

from roadmap_ai.exporters import (
    build_roadmap_payload,
    default_export_path,
    export_json,
    export_markdown,
    render_markdown,
)
from roadmap_ai.models import Roadmap, RoadmapLevel


def test_markdown_contains_structure_and_progress(roadmap: Roadmap) -> None:
    markdown = render_markdown(roadmap, completed_levels=[1])

    assert "# Roadmap: Sistemas de control" in markdown
    assert "## Nivel 1:" in markdown
    assert "### Objetivo" in markdown
    assert "### Prerrequisitos" in markdown
    assert "### Conceptos clave" in markdown
    assert "### Recursos" in markdown
    assert "### Proyecto práctico" in markdown
    assert "## Progreso" in markdown
    assert "- [x] Nivel 1" in markdown
    assert "- [ ] Nivel 2" in markdown
    resource = roadmap.levels[0].resources[0]
    assert f"]({resource.url})" in markdown


def test_markdown_exports_resource_metadata(roadmap: Roadmap) -> None:
    markdown = render_markdown(roadmap)

    resource = roadmap.levels[0].resources[0]
    assert f"Tipo: {resource.type.value}" in markdown
    assert f"Fuente: {resource.source}" in markdown
    assert resource.summary in markdown


def test_markdown_reports_insufficient_resources() -> None:
    roadmap = Roadmap(
        topic="tema",
        title="Roadmap de Tema",
        levels=[RoadmapLevel(number=1, title="Nivel vacío")],
    )

    assert "Recursos insuficientes." in render_markdown(roadmap)


def test_json_payload_has_expected_fields(roadmap: Roadmap) -> None:
    payload = build_roadmap_payload(roadmap, completed_levels=[1])

    assert payload["topic"] == "sistemas de control"
    assert payload["title"] == "Roadmap de Sistemas de control"
    assert payload["created_at"]
    assert payload["completed_levels"] == [1]
    assert len(payload["levels"]) == len(roadmap.levels)
    first_resource = payload["levels"][0]["resources"][0]
    assert {
        "type",
        "title",
        "authors",
        "year",
        "url",
        "doi",
        "source",
        "open_access",
        "summary",
        "relevance_score",
    } <= set(first_resource)
    assert first_resource["url"].startswith("https://")


def test_exporters_write_utf8_files(roadmap: Roadmap, tmp_path) -> None:
    markdown_path = export_markdown(roadmap, tmp_path / "roadmap.md")
    json_path = export_json(roadmap, tmp_path / "roadmap.json")

    assert "Sistemas de control" in markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["topic"] == "sistemas de control"


def test_default_export_path_uses_topic_and_id(roadmap: Roadmap) -> None:
    path = default_export_path(roadmap, "json")

    assert path.name == f"sistemas-de-control-{roadmap.id[:8]}.json"
    assert path.parent.name == "exports"
