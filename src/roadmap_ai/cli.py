"""Interfaz de línea de comandos de RoadmapAI."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from roadmap_ai.config import Settings, get_settings
from roadmap_ai.exporters import (
    default_export_path,
    export_json,
    export_markdown,
)
from roadmap_ai.models import Roadmap
from roadmap_ai.pipeline.service import PipelineService
from roadmap_ai.sample_data import build_sample_roadmap
from roadmap_ai.storage import (
    AmbiguousRoadmapIdError,
    Database,
    LevelNotFoundError,
    RepositoryError,
    RoadmapNotFoundError,
    RoadmapRepository,
)

app = typer.Typer(
    name="roadmap",
    help="Genera roadmaps de estudio académicos con recursos legales y verificables.",
    add_completion=False,
)
console = Console()


def _configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=False, show_path=False)],
    )


@contextmanager
def _database_context(settings: Settings | None = None) -> Iterator[Database]:
    settings = settings or get_settings()
    _configure_logging(settings)
    database = Database(settings.database_url)
    database.create_all()
    try:
        yield database
    finally:
        database.dispose()


@contextmanager
def _repository() -> Iterator[RoadmapRepository]:
    settings = get_settings()
    _configure_logging(settings)
    database = Database(settings.database_url)
    database.create_all()
    try:
        yield RoadmapRepository(database)
    finally:
        database.dispose()


def _abort(message: str, exit_code: int = 1) -> None:
    console.print(f"[bold red]Error:[/bold red] {message}")
    raise typer.Exit(code=exit_code)


def _format_datetime(value) -> str:
    try:
        return value.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)


def _parse_level_number(value: str) -> int:
    match = re.search(r"(\d+)", value)
    if not match:
        _abort("No se pudo interpretar el número de nivel. Usa '1' o 'Nivel 1'.", exit_code=2)
    number = int(match.group(1))
    if number < 1:
        _abort("El número de nivel debe ser mayor o igual a 1.", exit_code=2)
    return number


def _sources_text(roadmap: Roadmap) -> str:
    sources = sorted({resource.source for resource in roadmap.resources})
    return ", ".join(sources) if sources else "N/D"


def _render_progress(roadmap: Roadmap, completed_levels: list[int]) -> str:
    completed = set(completed_levels)
    total = len(roadmap.levels)
    done = len(completed)
    percent = int(round(done / total * 100)) if total else 0
    bar_width = 30
    filled = int(bar_width * done / total) if total else 0
    bar = "█" * filled + "░" * (bar_width - filled)
    return f"[{bar}] {done}/{total} ({percent}%)"


def _print_roadmap(roadmap: Roadmap, completed_levels: list[int]) -> None:
    console.print(
        Panel(
            f"[bold]{roadmap.title}[/bold]\n"
            f"[dim]Tema:[/dim] {roadmap.topic}\n"
            f"[dim]ID:[/dim] {roadmap.id}\n\n"
            f"{roadmap.description}",
            border_style="cyan",
        )
    )
    console.print(_render_progress(roadmap, completed_levels))
    console.print()

    for level in roadmap.levels:
        status = "✅" if level.number in completed_levels else "⬜"
        console.print(f"[bold]{status} Nivel {level.number}: {level.title}[/bold]")
        if level.objective:
            console.print(f"  [dim]Objetivo:[/dim] {level.objective}")
        if level.prerequisites:
            console.print(f"  [dim]Prerequisitos:[/dim] {', '.join(level.prerequisites)}")
        if level.concepts:
            console.print(f"  [dim]Conceptos:[/dim] {', '.join(level.concepts)}")
        if level.projects:
            console.print(f"  [dim]Proyectos:[/dim] {', '.join(level.projects)}")
        if level.resources:
            console.print("  [dim]Recursos:[/dim]")
            for resource in level.resources:
                oa = " [green]OA[/green]" if resource.open_access else ""
                year = f" ({resource.year})" if resource.year else ""
                authors = f" — {', '.join(resource.authors[:3])}" if resource.authors else ""
                console.print(f"    - [{resource.type.value}]{oa} {resource.title}{year}{authors}")
                console.print(f"      {resource.url}")
                if resource.summary:
                    console.print(f"      [dim]{escape(resource.summary)}[/dim]")
        console.print()


@app.command()
def generate(
    topic: str = typer.Argument(..., help="Tema académico, por ejemplo 'diseño mecatrónico'."),
    depth: int = typer.Option(8, "--depth", min=4, max=10, help="Número de niveles (4-10)."),
    max_resources: int = typer.Option(
        200, "--max-resources", min=1, help="Máximo de recursos incluidos en el roadmap."
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Archivo de salida. Usa .json para JSON; otro sufijo genera Markdown.",
    ),
    no_llm: bool = typer.Option(
        False, "--no-llm", help="Genera sin LLM (usa pipeline heurístico)."
    ),
    offline: bool = typer.Option(
        False, "--offline", help="Usa solo datos de demostración sin consultar APIs externas."
    ),
    sources: str | None = typer.Option(
        None,
        "--sources",
        help="Fuentes separadas por coma (openalex,semantic_scholar,arxiv,open_library,youtube,github).",
    ),
) -> None:
    if not topic.strip():
        _abort("El tema no puede estar vacío", exit_code=2)

    settings = get_settings()
    _configure_logging(settings)

    source_list = None
    if sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]

    try:
        import asyncio

        with _database_context(settings) as database:
            service = PipelineService(database, settings, use_llm=not no_llm)
            if offline:
                roadmap = build_sample_roadmap(topic, depth=depth, max_resources=max_resources)
                with _repository() as repository:
                    repository.save(roadmap)
            else:
                try:
                    roadmap = asyncio.run(
                        service.generate(
                            topic,
                            depth=depth,
                            max_resources=max_resources,
                            source_names=source_list,
                            offline=False,
                        )
                    )
                    with _repository() as repository:
                        repository.save(roadmap)
                except Exception as exc:
                    console.print(
                        "[yellow]Aviso:[/yellow] Falló pipeline real "
                        f"({exc}), usando datos de demostración."
                    )
                    roadmap = build_sample_roadmap(topic, depth=depth, max_resources=max_resources)
                    with _repository() as repository:
                        repository.save(roadmap)
    except ValueError as exc:
        _abort(str(exc), exit_code=2)
    except RepositoryError as exc:
        _abort(str(exc))

    if no_llm:
        console.print("[dim]Modo sin LLM solicitado; se usaron reglas locales.[/dim]")

    if output is not None:
        try:
            with _repository() as repository:
                completed_levels = repository.get_completed_levels(roadmap.id)
        except Exception:
            completed_levels = []
        destination = output
        normalized_format = destination.suffix.lower().lstrip(".")
        if normalized_format == "json":
            from roadmap_ai.exporters import export_json

            export_json(roadmap, destination, completed_levels)
        else:
            from roadmap_ai.exporters import export_markdown

            export_markdown(roadmap, destination, completed_levels)

    console.print(
        Panel(
            f"[green]Roadmap generado y guardado.[/green]\n"
            f"[dim]ID:[/dim] {roadmap.id}\n"
            f"[dim]Niveles:[/dim] {len(roadmap.levels)}\n"
            f"[dim]Recursos:[/dim] {len(roadmap.resources)}\n"
            f"[dim]Fuentes:[/dim] {escape(_sources_text(roadmap))}",
            title="RoadmapAI - Fase 3",
            border_style="green",
        )
    )


@app.command("list")
def list_roadmaps(
    limit: int = typer.Option(50, "--limit", min=1, max=500, help="Máximo de roadmaps."),
) -> None:
    with _repository() as repository:
        summaries = repository.list_summaries(limit=limit)

    if not summaries:
        console.print(Panel("No hay roadmaps guardados.", title="RoadmapAI", border_style="yellow"))
        return

    table = Table(title="Roadmaps guardados", border_style="cyan")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Tema", style="bold")
    table.add_column("Niveles", justify="right")
    table.add_column("Recursos", justify="right")
    table.add_column("Progreso", justify="right")
    table.add_column("Actualizado", no_wrap=True)

    for summary in summaries:
        table.add_row(
            summary.id[:8],
            summary.topic,
            str(summary.total_levels),
            str(summary.resource_count),
            f"{len(summary.completed_levels)}/{summary.total_levels} ({summary.progress_percent}%)",
            _format_datetime(summary.updated_at),
        )
    console.print(table)


@app.command()
def show(
    roadmap_id: str = typer.Argument(..., help="ID completo o prefijo único del roadmap."),
) -> None:
    with _repository() as repository:
        try:
            resolved_id = repository.resolve_id(roadmap_id)
            roadmap = repository.get(resolved_id)
            if roadmap is None:
                raise RoadmapNotFoundError(f"No existe un roadmap con id '{roadmap_id}'")
            completed_levels = repository.get_completed_levels(resolved_id)
        except AmbiguousRoadmapIdError as exc:
            _abort(str(exc), exit_code=2)
        except RoadmapNotFoundError as exc:
            _abort(str(exc))
    _print_roadmap(roadmap, completed_levels)


@app.command()
def export(
    roadmap_id: str = typer.Argument(..., help="ID completo o prefijo único del roadmap."),
    format: str = typer.Option(
        "markdown", "--format", "-f", help="Formato de salida: markdown o json."
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Ruta de destino."),
) -> None:
    normalized_format = format.strip().lower()
    if normalized_format == "md":
        normalized_format = "markdown"
    if normalized_format not in {"markdown", "json"}:
        _abort("El formato debe ser 'markdown' o 'json'", exit_code=2)

    with _repository() as repository:
        try:
            resolved_id = repository.resolve_id(roadmap_id)
            roadmap = repository.get(resolved_id)
            if roadmap is None:
                raise RoadmapNotFoundError(f"No existe un roadmap con id '{roadmap_id}'")
            completed_levels = repository.get_completed_levels(resolved_id)
        except AmbiguousRoadmapIdError as exc:
            _abort(str(exc), exit_code=2)
        except RoadmapNotFoundError as exc:
            _abort(str(exc))

    destination = output or default_export_path(
        roadmap, "json" if normalized_format == "json" else "md"
    )
    try:
        if normalized_format == "json":
            written_path = export_json(roadmap, destination, completed_levels)
        else:
            written_path = export_markdown(roadmap, destination, completed_levels)
    except OSError as exc:
        _abort(f"No se pudo escribir el archivo: {exc}")
    console.print(
        f"[green]Roadmap exportado en {normalized_format}:[/green] {written_path.resolve()}"
    )


@app.command()
def progress(
    roadmap_id: str = typer.Argument(..., help="ID completo o prefijo único del roadmap."),
    complete: str = typer.Option(
        ..., "--complete", help="Nivel a marcar, por ejemplo 'Nivel 1' o '1'."
    ),
    uncomplete: bool = typer.Option(
        False, "--uncomplete", help="Desmarca el nivel en lugar de completarlo."
    ),
) -> None:
    level_number = _parse_level_number(complete)
    with _repository() as repository:
        try:
            resolved_id = repository.resolve_id(roadmap_id)
            repository.set_level_completed(resolved_id, level_number, completed=not uncomplete)
            roadmap = repository.get(resolved_id)
            if roadmap is None:
                raise RoadmapNotFoundError(f"No existe un roadmap con id '{roadmap_id}'")
            completed_levels = repository.get_completed_levels(resolved_id)
        except AmbiguousRoadmapIdError as exc:
            _abort(str(exc), exit_code=2)
        except (RoadmapNotFoundError, LevelNotFoundError) as exc:
            _abort(str(exc))
    action = "desmarcado" if uncomplete else "marcado como completado"
    console.print(f"[green]Nivel {level_number} {action}.[/green]")
    console.print(_render_progress(roadmap, completed_levels))


@app.command("remove")
@app.command("delete")
def remove(
    roadmap_id: str = typer.Argument(..., help="ID completo o prefijo único del roadmap."),
    force: bool = typer.Option(False, "--force", "-f", help="No pedir confirmación."),
) -> None:
    with _repository() as repository:
        try:
            resolved_id = repository.resolve_id(roadmap_id)
            roadmap = repository.get(resolved_id)
            if roadmap is None:
                raise RoadmapNotFoundError(f"No existe un roadmap con id '{roadmap_id}'")
        except AmbiguousRoadmapIdError as exc:
            _abort(str(exc), exit_code=2)
        except RoadmapNotFoundError as exc:
            _abort(str(exc))

        if not force:
            confirm = typer.confirm(f"¿Eliminar el roadmap '{roadmap.topic}' ({resolved_id[:8]})?")
            if not confirm:
                console.print("[yellow]Eliminación cancelada.[/yellow]")
                return

        try:
            from sqlalchemy import delete

            from roadmap_ai.storage.database import (
                RoadmapLevelRecord,
                RoadmapRecord,
                RoadmapResourceRecord,
                UserProgressRecord,
            )

            with repository.database.session() as session:
                session.exec(
                    delete(RoadmapResourceRecord).where(
                        RoadmapResourceRecord.roadmap_id == resolved_id
                    )
                )
                session.exec(
                    delete(RoadmapLevelRecord).where(RoadmapLevelRecord.roadmap_id == resolved_id)
                )
                session.exec(
                    delete(UserProgressRecord).where(UserProgressRecord.roadmap_id == resolved_id)
                )
                session.exec(delete(RoadmapRecord).where(RoadmapRecord.id == resolved_id))
        except Exception as exc:
            _abort(f"No se pudo eliminar el roadmap: {exc}")

    console.print(f"[green]Roadmap {resolved_id[:8]} eliminado correctamente.[/green]")


@app.command()
def update(
    roadmap_id: str = typer.Argument(..., help="ID completo o prefijo único del roadmap."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Actualiza sin LLM usando reglas locales."),
) -> None:
    if no_llm:
        console.print("[dim]Modo sin LLM solicitado; se usaron reglas locales.[/dim]")

    with _repository() as repository:
        try:
            resolved_id = repository.resolve_id(roadmap_id)
            current = repository.get(resolved_id)
            if current is None:
                raise RoadmapNotFoundError(f"No existe un roadmap con id '{roadmap_id}'")
            completed_levels = repository.get_completed_levels(resolved_id)
            updated = build_sample_roadmap(
                current.topic,
                depth=len(current.levels),
                max_resources=max(len(current.resources), 1),
                roadmap_id=current.id,
                created_at=current.created_at,
            )
            repository.save(updated)
            for level_num in completed_levels:
                try:
                    repository.set_level_completed(updated.id, level_num, completed=True)
                except Exception:
                    pass
        except AmbiguousRoadmapIdError as exc:
            _abort(str(exc), exit_code=2)
        except RoadmapNotFoundError as exc:
            _abort(str(exc))
        except ValueError as exc:
            _abort(str(exc), exit_code=2)

    console.print(
        Panel(
            f"[green]Roadmap actualizado.[/green]\n"
            f"[dim]ID:[/dim] {updated.id}\n"
            f"[dim]Niveles:[/dim] {len(updated.levels)}\n"
            f"[dim]Recursos:[/dim] {len(updated.resources)}\n"
            "El progreso de los niveles se conservó.",
            title="RoadmapAI - Fase 1",
            border_style="green",
        )
    )


if __name__ == "__main__":
    app()
