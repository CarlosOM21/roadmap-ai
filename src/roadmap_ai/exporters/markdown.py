"""Exportación de roadmaps a Markdown legible."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from roadmap_ai.models import Roadmap


def _escape_link_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _join_items(items: Iterable[str], empty_text: str) -> list[str]:
    values = [item.strip() for item in items if item and item.strip()]
    if not values:
        return [f"- {empty_text}"]
    return [f"- {item}" for item in values]


def render_markdown(roadmap: Roadmap, completed_levels: Iterable[int] = ()) -> str:
    """Renderiza un roadmap como Markdown.

    Args:
        roadmap: Roadmap de dominio a exportar.
        completed_levels: Números de nivel ya completados.
    """
    completed = set(completed_levels)
    display_topic = roadmap.topic[0].upper() + roadmap.topic[1:]
    lines = [f"# Roadmap: {display_topic}", ""]

    if roadmap.description:
        lines.extend([roadmap.description, ""])

    for level in sorted(roadmap.levels, key=lambda item: item.number):
        lines.extend(
            [
                f"## Nivel {level.number}: {level.title}",
                "",
                "### Objetivo",
                level.objective or "Objetivo no especificado.",
                "",
                "### Prerrequisitos",
                *_join_items(level.prerequisites, "No especificados."),
                "",
                "### Conceptos clave",
                *_join_items(level.concepts, "No especificados."),
                "",
                "### Recursos",
            ]
        )

        if not level.resources:
            lines.append("- Recursos insuficientes.")
        for resource in level.resources:
            year = str(resource.year) if resource.year else "s. f."
            metadata = f"Tipo: {resource.type.value} — Fuente: {resource.source} — Año: {year}"
            if resource.open_access:
                metadata += " — Acceso abierto"
            if resource.doi:
                metadata += f" — DOI: {resource.doi}"
            lines.append(f"- [{_escape_link_text(resource.title)}]({resource.url}) — {metadata}  ")
            if resource.summary:
                lines.append(f"  {resource.summary}")

        lines.extend(
            [
                "",
                "### Proyecto práctico",
                *_join_items(level.projects, "No especificado."),
                "",
            ]
        )

    lines.extend(["## Progreso"])
    for level in sorted(roadmap.levels, key=lambda item: item.number):
        mark = "x" if level.number in completed else " "
        lines.append(f"- [{mark}] Nivel {level.number}")

    if roadmap.queries_used:
        lines.extend(["", "## Queries utilizadas"])
        lines.extend(f"- `{query}`" for query in roadmap.queries_used)

    return "\n".join(lines).rstrip() + "\n"


def export_markdown(
    roadmap: Roadmap,
    path: Path,
    completed_levels: Iterable[int] = (),
) -> Path:
    """Escribe el roadmap en un archivo Markdown y devuelve su ruta."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_markdown(roadmap, completed_levels),
        encoding="utf-8",
    )
    return destination


__all__ = ["export_markdown", "render_markdown"]
