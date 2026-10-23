"""Datos de demostración para la Fase 1.

Los recursos usan URLs públicas reales y se marcan con ``raw_metadata.demo`` para
que el usuario sepa que todavía no proceden del pipeline de recuperación.
"""

from __future__ import annotations

from datetime import datetime

from roadmap_ai.models import (
    Resource,
    ResourceType,
    Roadmap,
    RoadmapLevel,
    new_id,
    utc_now,
)

DEMO_RESOURCES: dict[str, Resource] = {
    "openstax-calculus": Resource(
        id="demo-openstax-calculus",
        type=ResourceType.BOOK,
        title="Calculus Volume 1",
        authors=["Gilbert Strang", "Edwin Herman"],
        year=2016,
        url="https://openstax.org/details/books/calculus-volume-1",
        source="OpenStax",
        summary="Libro abierto de cálculo diferencial e integral con aplicaciones.",
        open_access=True,
        relevance_score=0.84,
        raw_metadata={"demo": True},
    ),
    "mit-1806": Resource(
        id="demo-mit-1806",
        type=ResourceType.COURSE,
        title="18.06 Linear Algebra",
        authors=["Gilbert Strang"],
        year=2010,
        url="https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/",
        source="MIT OpenCourseWare",
        summary="Curso completo de álgebra lineal con vídeos, apuntes y ejercicios.",
        open_access=True,
        relevance_score=0.86,
        raw_metadata={"demo": True},
    ),
    "mit-6003": Resource(
        id="demo-mit-6003",
        type=ResourceType.COURSE,
        title="6.003 Signals and Systems",
        authors=[],
        year=2011,
        url="https://ocw.mit.edu/courses/6-003-signals-and-systems-fall-2011/",
        source="MIT OpenCourseWare",
        summary="Fundamentos de señales, sistemas lineales, convolución y Fourier.",
        open_access=True,
        relevance_score=0.83,
        raw_metadata={"demo": True},
    ),
    "wikibooks-control": Resource(
        id="demo-wikibooks-control",
        type=ResourceType.BOOK,
        title="Control Systems",
        authors=["Wikibooks contributors"],
        year=None,
        url="https://en.wikibooks.org/wiki/Control_Systems",
        source="Wikibooks",
        summary="Libro abierto sobre modelado, estabilidad y diseño de sistemas de control.",
        open_access=True,
        relevance_score=0.86,
        raw_metadata={"demo": True},
    ),
    "mit-1606": Resource(
        id="demo-mit-1606",
        type=ResourceType.COURSE,
        title="16.06 Principles of Automatic Control",
        authors=[],
        year=2012,
        url="https://ocw.mit.edu/courses/16-06-principles-of-automatic-control-fall-2012/",
        source="MIT OpenCourseWare",
        summary="Principios de control automático, estabilidad y diseño de lazos.",
        open_access=True,
        relevance_score=0.88,
        raw_metadata={"demo": True},
    ),
    "python-control": Resource(
        id="demo-python-control",
        type=ResourceType.DOCUMENTATION,
        title="Python Control Systems Library",
        authors=["Python Control Developers"],
        year=None,
        url="https://python-control.readthedocs.io/en/latest/",
        source="Python Control",
        summary="Documentación para analizar y diseñar sistemas de control en Python.",
        open_access=True,
        relevance_score=0.87,
        raw_metadata={"demo": True},
    ),
    "scipy-signal": Resource(
        id="demo-scipy-signal",
        type=ResourceType.DOCUMENTATION,
        title="SciPy Signal Processing",
        authors=["SciPy Developers"],
        year=None,
        url="https://docs.scipy.org/doc/scipy/reference/signal.html",
        source="SciPy",
        summary="Herramientas de procesamiento de señales, filtros y análisis espectral.",
        open_access=True,
        relevance_score=0.79,
        raw_metadata={"demo": True},
    ),
    "arduino-pid": Resource(
        id="demo-arduino-pid",
        type=ResourceType.TOOL,
        title="Arduino PID Library",
        authors=["Brett Beauregard"],
        year=None,
        url="https://github.com/br3ttb/Arduino-PID-Library",
        source="GitHub",
        summary="Implementación abierta de un controlador PID para proyectos embebidos.",
        open_access=True,
        relevance_score=0.75,
        raw_metadata={"demo": True},
    ),
    "recht-rl-control": Resource(
        id="demo-recht-rl-control",
        type=ResourceType.PAPER,
        title="A Tour of Reinforcement Learning: The View from Continuous Control",
        authors=["Benjamin Recht"],
        year=2018,
        url="https://arxiv.org/abs/1806.09460",
        doi="10.1146/annurev-control-053018-023825",
        source="arXiv",
        summary="Panorama de aprendizaje por refuerzo aplicado al control continuo.",
        open_access=True,
        relevance_score=0.82,
        citation_count=600,
        raw_metadata={"demo": True, "arxiv_id": "1806.09460"},
    ),
}


def _level(
    number: int,
    title: str,
    objective: str,
    prerequisites: list[str],
    concepts: list[str],
    projects: list[str],
    resource_ids: list[str],
    selected: set[str],
    remaining: int,
) -> RoadmapLevel:
    resources: list[Resource] = []
    for resource_id in resource_ids:
        if remaining <= 0:
            break
        if resource_id in selected:
            continue
        resources.append(DEMO_RESOURCES[resource_id])
        selected.add(resource_id)
        remaining -= 1

    return RoadmapLevel(
        number=number,
        title=title,
        objective=objective,
        prerequisites=prerequisites,
        concepts=concepts,
        projects=projects,
        resources=resources,
    )


def build_sample_roadmap(
    topic: str,
    depth: int = 5,
    max_resources: int = 30,
    *,
    roadmap_id: str | None = None,
    created_at: datetime | None = None,
) -> Roadmap:
    """Construye un roadmap de demostración determinista y verificable.

    Args:
        topic: Tema académico indicado por el usuario.
        depth: Número de niveles, entre 4 y 6.
        max_resources: Límite total de recursos incluidos.
        roadmap_id: Identificador a conservar al actualizar un roadmap.
        created_at: Fecha original a conservar al actualizar.
    """
    normalized_topic = topic.strip()
    if not normalized_topic:
        raise ValueError("El tema no puede estar vacío")
    if not 4 <= depth <= 6:
        raise ValueError("La profundidad debe estar entre 4 y 6 niveles")
    if max_resources < 1:
        raise ValueError("Debe incluirse al menos un recurso")

    selected: set[str] = set()
    remaining = max_resources
    levels = [
        _level(
            1,
            "Fundamentos matemáticos",
            "Construir la base de cálculo y álgebra lineal necesaria para modelar sistemas.",
            ["Álgebra básica", "Cálculo diferencial"],
            [
                "Límites e integrales",
                "Matrices",
                "Espacios vectoriales",
                "Ecuaciones diferenciales",
            ],
            ["Resolver problemas de cálculo aplicados a modelos dinámicos."],
            ["openstax-calculus", "mit-1806"],
            selected,
            remaining,
        ),
        _level(
            2,
            "Señales y sistemas",
            "Comprender señales, sistemas lineales y representaciones en frecuencia.",
            ["Fundamentos matemáticos"],
            ["Convolución", "Transformada de Laplace", "Series de Fourier", "Sistemas LTI"],
            ["Analizar una señal con Python y describir su respuesta en frecuencia."],
            ["mit-6003"],
            selected,
            remaining - len(selected),
        ),
        _level(
            3,
            "Teoría de control",
            "Modelar lazos de realimentación y evaluar estabilidad y respuesta dinámica.",
            ["Señales y sistemas"],
            ["Funciones de transferencia", "Estabilidad", "Realimentación", "Lugar de las raíces"],
            ["Diseñar y simular un lazo de control para una planta sencilla."],
            ["wikibooks-control", "mit-1606"],
            selected,
            remaining - len(selected),
        ),
        _level(
            4,
            "Herramientas y práctica",
            "Implementar análisis y diseño de control con herramientas computacionales.",
            ["Teoría de control", "Programación básica en Python"],
            ["Análisis de respuesta", "Filtros", "Simulación", "Sintonización"],
            ["Comparar controladores P, PI y PID sobre un modelo simulado."],
            ["python-control", "scipy-signal"],
            selected,
            remaining - len(selected),
        ),
        _level(
            5,
            "Aplicación y proyectos",
            "Integrar los conceptos en un prototipo funcional y documentado.",
            ["Herramientas y práctica"],
            ["Control PID", "Sensores y actuadores", "Validación experimental"],
            ["Construir un controlador PID para un sistema físico o emulado."],
            ["arduino-pid"],
            selected,
            remaining - len(selected),
        ),
        _level(
            6,
            "Especialización e investigación",
            "Explorar técnicas avanzadas y literatura científica sobre control y aprendizaje.",
            ["Aplicación y proyectos"],
            ["Aprendizaje por refuerzo", "Control óptimo", "Evaluación experimental"],
            ["Leer un paper y reproducir un experimento simplificado."],
            ["recht-rl-control"],
            selected,
            remaining - len(selected),
        ),
    ]

    display_topic = normalized_topic[0].upper() + normalized_topic[1:]
    timestamp = utc_now()
    queries = [
        f"{normalized_topic} fundamentos matemáticos",
        f"{normalized_topic} señales y sistemas",
        f"{normalized_topic} teoría de control",
        f"{normalized_topic} herramientas python",
        f"{normalized_topic} proyectos aplicados",
        f"{normalized_topic} investigación reciente",
    ]

    return Roadmap(
        id=roadmap_id or new_id(),
        topic=normalized_topic,
        title=f"Roadmap de {display_topic}",
        description=(
            "Roadmap progresivo de demostración. En fases posteriores los recursos "
            "serán recuperados y puntuados automáticamente desde fuentes académicas."
        ),
        levels=levels[:depth],
        queries_used=queries[:depth],
        created_at=created_at or timestamp,
        updated_at=timestamp,
    )


__all__ = ["DEMO_RESOURCES", "build_sample_roadmap"]
