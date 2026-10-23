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
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
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
    help="Genera y gestiona roadmaps académicos con fuentes verificables.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _configure_logging(settings: Settings) -> None:
    logger = logging.getLogger("roadmap_ai")
    logger.setLevel(settings.log_level)
    logger.propagate = False

    if any(getattr(handler, "_roadmap_ai_handler", False) for handler in logger.handlers):
        return

    handler = RichHandler(
        console=Console(stderr=True),
        show_time=False,
        show_path=False,
        markup=False,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler._roadmap_ai_handler = True
    logger.addHandler(handler)


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
    console.print(f"[bold red]Error:[/bold red] {escape(message)}")
    raise typer.Exit(exit_code)


def _format_datetime(value: object) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _parse_level_number(value: str) -> int:
    match = re.fullmatch(r"\s*(?:nivel\s*)?(\d+)\s*", value, flags=re.IGNORECASE)
    if not match:
        raise typer.BadParameter("Usa un formato como 'Nivel 1' o '1'")
    return int(match.group(1))


def _render_progress(roadmap: Roadmap, completed_levels: list[int]) -> Progress:
    progress = Progress(
        TextColumn("[bold]Progreso"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )
    progress.add_task(
        "Progreso",
        total=len(roadmap.levels),
        completed=len(set(completed_levels)),
    )
    return progress


def _sources_text(roadmap: Roadmap) -> str:
    sources = sorted({resource.source for resource in roadmap.resources})
    return ", ".join(sources) if sources else "ninguna"


def _print_roadmap(roadmap: Roadmap, completed_levels: list[int]) -> None:
    completed = set(completed_levels)
    console.print(
        Panel(
            f"[bold]{escape(roadmap.title)}[/bold]\n"
            f"[dim]ID:[/dim] {roadmap.id}\n"
            f"[dim]Tema:[/dim] {escape(roadmap.topic)}\n"
            f"[dim]Creado:[/dim] {_format_datetime(roadmap.created_at)}\n"
            f"[dim]Actualizado:[/dim] {_format_datetime(roadmap.updated_at)}\n"
            f"[dim]Fuentes de los recursos:[/dim] {escape(_sources_text(roadmap))}\n"
            f"{escape(roadmap.description)}",
            title="RoadmapAI",
            border_style="cyan",
        )
    )
    console.print(_render_progress(roadmap, completed_levels))
    console.print()

    for level in sorted(roadmap.levels, key=lambda item: item.number):
        state = "[green]completado[/green]" if level.number in completed else "[dim]pendiente[/dim]"
        prerequisites = ", ".join(level.prerequisites) or "No especificados"
        concepts = ", ".join(level.concepts) or "No especificados"
        projects = "\n".join(f"• {escape(project)}" for project in level.projects)
        if not projects:
            projects = "• No especificado"

        resource_lines: list[str] = []
        if not level.resources:
            resource_lines.append("[yellow]Recursos insuficientes.[/yellow]")
        for resource in level.resources:
            year = resource.year or "s. f."
            resource_lines.append(
                f"[cyan]•[/cyan] {escape(resource.title)} "
                f"[dim]({resource.type.value}, {year}, {escape(resource.source)})[/dim]\n"
                f"  [blue]{escape(resource.url)}[/blue]"
            )

        content = (
            f"[bold]Objetivo:[/bold] {escape(level.objective or 'No especificado')}\n"
            f"[bold]Prerrequisitos:[/bold] {escape(prerequisites)}\n"
            f"[bold]Conceptos:[/bold] {escape(concepts)}\n\n"
            f"[bold]Recursos[/bold]\n" + "\n".join(resource_lines) + "\n\n"
            f"[bold]Proyecto práctico[/bold]\n{projects}"
        )
        console.print(
            Panel(
                content,
                title=f"Nivel {level.number}: {escape(level.title)} [{state}]",
                border_style="green" if level.number in completed else "blue",
            )
        )

    if roadmap.queries_used:
        console.print("[bold]Queries utilizadas[/bold]")
        for query in roadmap.queries_used:
            console.print(f"• [dim]{escape(query)}[/dim]")


@app.callback()
def main() -> None:
    """Genera, consulta y exporta roadmaps académicos."""


@app.command()
def generate(
    topic: str = typer.Argument(..., help="Tema académico, por ejemplo 'inteligencia artificial'."),
    depth: int = typer.Option(6, "--depth", min=4, max=8, help="Número de niveles (4-8)."),
    max_resources: int = typer.Option(
        80,
        "--max-resources",
        min=1,
        help="Máximo de recursos incluidos en el roadmap.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Archivo de salida. Usa .json para JSON; otro sufijo genera Markdown.",
    ),
    no_llm: bool = typer.Option(
        False,
        "--no-llm",
        help="Genera sin LLM (usa pipeline heurístico).",
    ),
    offline: bool = typer.Option(
        False,
        "--offline",
        help="Usa solo datos de demostración sin consultar APIs externas.",
    ),
    sources: str | None = typer.Option(
        None,
        "--sources",
        help="Fuentes separadas por coma (openalex,semantic_scholar,arxiv,open_library,youtube).",
    ),
) -> None:
    """Genera un roadmap usando el pipeline real o datos de demostración."""
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
    if offline or not source_list:
        console.print(
            "[yellow]Aviso:[/yellow] Usa --offline para datos demo o las APIs externas "
            "se consultan según configuración. Los recursos deben tener URLs verificables."
        )

    if output is not None:
        try:
            if output.suffix.lower() == ".json":
                destination = export_json(roadmap, output)
            else:
                destination = export_markdown(roadmap, output)
        except OSError as exc:
            _abort(f"No se pudo escribir el archivo: {exc}")
        console.print(f"[green]Exportado a:[/green] {destination.resolve()}")


@app.command("list")
def list_roadmaps(
    limit: int = typer.Option(50, "--limit", min=1, max=500, help="Máximo de roadmaps."),
) -> None:
    """Lista los roadmaps guardados y su progreso."""
    with _repository() as repository:
        summaries = repository.list_summaries(limit=limit)

    if not summaries:
        console.print(
            Panel(
                "No hay roadmaps guardados.\n"
                'Ejecuta: [bold]roadmap generate "sistemas de control"[/bold]',
                title="RoadmapAI",
                border_style="yellow",
            )
        )
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
    """Muestra un roadmap guardado sin llamar a APIs externas."""
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
        "markdown",
        "--format",
        "-f",
        help="Formato de salida: markdown o json.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Ruta de destino. Si se omite, se escribe en exports/.",
    ),
) -> None:
    """Exporta un roadmap guardado a Markdown o JSON."""
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
        roadmap,
        "json" if normalized_format == "json" else "md",
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
        ...,
        "--complete",
        help="Nivel a marcar, por ejemplo 'Nivel 1' o '1'.",
    ),
    uncomplete: bool = typer.Option(
        False,
        "--uncomplete",
        help="Desmarca el nivel en lugar de completarlo.",
    ),
) -> None:
    """Marca o desmarca el progreso de un nivel."""
    level_number = _parse_level_number(complete)

    with _repository() as repository:
        try:
            resolved_id = repository.resolve_id(roadmap_id)
            repository.set_level_completed(
                resolved_id,
                level_number,
                completed=not uncomplete,
            )
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
    """Elimina un roadmap y su progreso."""
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
            # Eliminar con integridad referencial
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
    no_llm: bool = typer.Option(
        False,
        "--no-llm",
        help="Actualiza sin LLM usando reglas locales.",
    ),
) -> None:
    """Actualiza un roadmap conservando su ID y su progreso."""
    if no_llm:
        console.print("[dim]Modo sin LLM solicitado; se usaron reglas locales.[/dim]")

    with _repository() as repository:
        try:
            resolved_id = repository.resolve_id(roadmap_id)
            current = repository.get(resolved_id)
            if current is None:
                raise RoadmapNotFoundError(f"No existe un roadmap con id '{roadmap_id}'")
            updated = build_sample_roadmap(
                current.topic,
                depth=len(current.levels),
                max_resources=max(len(current.resources), 1),
                roadmap_id=current.id,
                created_at=current.created_at,
            )
            repository.save(updated)
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


__all__ = ["app"]
