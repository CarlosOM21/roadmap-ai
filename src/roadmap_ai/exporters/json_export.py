"""Exportación de roadmaps a JSON estructurado."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from roadmap_ai.models import Resource, Roadmap


def _resource_payload(resource: Resource) -> dict[str, Any]:
    return {
        "type": resource.type.value,
        "title": resource.title,
        "authors": list(resource.authors),
        "year": resource.year,
        "url": resource.url,
        "doi": resource.doi,
        "source": resource.source,
        "open_access": resource.open_access,
        "summary": resource.summary,
        "relevance_score": round(resource.relevance_score, 4),
        "citation_count": resource.citation_count,
    }


def build_roadmap_payload(
    roadmap: Roadmap,
    completed_levels: Iterable[int] = (),
) -> dict[str, Any]:
    """Construye el diccionario JSON serializable de un roadmap."""
    return {
        "id": roadmap.id,
        "topic": roadmap.topic,
        "title": roadmap.title,
        "description": roadmap.description,
        "created_at": roadmap.created_at.isoformat(),
        "updated_at": roadmap.updated_at.isoformat(),
        "completed_levels": sorted(set(completed_levels)),
        "levels": [
            {
                "number": level.number,
                "title": level.title,
                "objective": level.objective,
                "prerequisites": list(level.prerequisites),
                "concepts": list(level.concepts),
                "projects": list(level.projects),
                "resources": [_resource_payload(resource) for resource in level.resources],
            }
            for level in sorted(roadmap.levels, key=lambda item: item.number)
        ],
        "queries_used": list(roadmap.queries_used),
    }


def render_json(roadmap: Roadmap, completed_levels: Iterable[int] = ()) -> str:
    """Renderiza el roadmap como JSON válido con indentación."""
    return (
        json.dumps(
            build_roadmap_payload(roadmap, completed_levels),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def export_json(
    roadmap: Roadmap,
    path: Path,
    completed_levels: Iterable[int] = (),
) -> Path:
    """Escribe el roadmap en un archivo JSON y devuelve su ruta."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_json(roadmap, completed_levels), encoding="utf-8")
    return destination


__all__ = ["build_roadmap_payload", "export_json", "render_json"]
