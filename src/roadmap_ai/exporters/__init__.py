"""Exportadores de roadmaps."""

from __future__ import annotations

from pathlib import Path

from roadmap_ai.exporters.json_export import (
    build_roadmap_payload,
    export_json,
    render_json,
)
from roadmap_ai.exporters.markdown import export_markdown, render_markdown
from roadmap_ai.models import Roadmap
from roadmap_ai.models import slugify as _slugify


def default_export_path(
    roadmap: Roadmap,
    extension: str,
    directory: Path | str = Path("exports"),
) -> Path:
    """Genera una ruta de salida estable a partir del tema y el id."""
    suffix = extension.lstrip(".")
    short_id = roadmap.id[:8]
    return Path(directory) / f"{_slugify(roadmap.topic)}-{short_id}.{suffix}"


__all__ = [
    "build_roadmap_payload",
    "default_export_path",
    "export_json",
    "export_markdown",
    "render_json",
    "render_markdown",
]
