"""Planificación curricular preliminar (Fase 3)."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from roadmap_ai.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class PlannedLevel(BaseModel):
    """Nivel propuesto por el planner antes de asignar recursos."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    number: int = Field(ge=1)
    title: str = Field(min_length=1)
    objective: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)


class PlannedRoadmap(BaseModel):
    """Estructura curricular previa a la recuperación de recursos."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: str = Field(min_length=1)
    levels: list[PlannedLevel] = Field(min_length=4, max_length=10)


@runtime_checkable
class Planner(Protocol):
    """Contrato del planificador curricular."""

    async def plan(self, topic: str, depth: int) -> PlannedRoadmap:
        """Genera una estructura de niveles y queries de búsqueda."""
        ...


class HeuristicPlanner:
    """Planificador heurístico determinista sin sesgo a un dominio."""

    async def plan(self, topic: str, depth: int) -> PlannedRoadmap:
        """Genera plan curricular escalonado y diverso para cualquier tema."""
        depth = max(6, min(10, depth))
        topic_clean = topic.strip()

        levels_data = []

        levels_data.append(
            PlannedLevel(
                number=1,
                title=f"Fundamentos, historia y panorama de {topic_clean}",
                objective=f"Comprender conceptos, terminología e historia de {topic_clean}",
                prerequisites=[],
                concepts=[
                    "Conceptos básicos",
                    "Terminología",
                    "Historia",
                    "Aplicaciones",
                    "Áreas relacionadas",
                ],
                projects=[f"Mapa conceptual y glosario de {topic_clean}"],
                queries=[
                    f"introduccion {topic_clean}",
                    f"fundamentos {topic_clean}",
                    f"{topic_clean} libro introductorio",
                    f"{topic_clean} curso basico",
                    f"historia {topic_clean}",
                    f"{topic_clean} guia principiantes",
                ],
            )
        )

        levels_data.append(
            PlannedLevel(
                number=2,
                title=f"Bases teóricas y herramientas para {topic_clean}",
                objective="Dominar bases teóricas, notación y herramientas",
                prerequisites=[f"Fundamentos, historia y panorama de {topic_clean}"],
                concepts=["Bases teóricas", "Notación", "Herramientas", "Recursos de consulta"],
                projects=[f"Configuración de entorno y ejercicios básicos de {topic_clean}"],
                queries=[
                    f"{topic_clean} fundamentos teoricos",
                    f"{topic_clean} libro fundamentos",
                    f"{topic_clean} tutorial",
                    f"{topic_clean} ejercicios",
                    f"{topic_clean} curso",
                    f"{topic_clean} documentacion",
                ],
            )
        )

        levels_data.append(
            PlannedLevel(
                number=3,
                title=f"Núcleo conceptual y técnicas clave de {topic_clean}",
                objective="Profundizar en conceptos centrales, técnicas y metodologías",
                prerequisites=[f"Bases teóricas y herramientas para {topic_clean}"],
                concepts=["Conceptos clave", "Técnicas", "Metodologías", "Análisis"],
                projects=[f"Resolución de ejercicios y mini-proyectos de {topic_clean}"],
                queries=[
                    f"{topic_clean} conceptos clave",
                    f"{topic_clean} tecnicas",
                    f"{topic_clean} metodologia",
                    f"{topic_clean} libro",
                    f"{topic_clean} ejercicios resueltos",
                    f"{topic_clean} ejemplos practicos",
                ],
            )
        )

        levels_data.append(
            PlannedLevel(
                number=4,
                title=f"Aplicaciones prácticas, casos de uso y proyectos guiados de {topic_clean}",
                objective="Aplicar conocimientos a problemas reales",
                prerequisites=[f"Núcleo conceptual y técnicas clave de {topic_clean}"],
                concepts=[
                    "Aplicaciones",
                    "Casos de uso",
                    "Implementación",
                    "Resolución de problemas",
                ],
                projects=[f"Proyecto guiado aplicando {topic_clean}"],
                queries=[
                    f"{topic_clean} aplicaciones practicas",
                    f"{topic_clean} casos de uso",
                    f"{topic_clean} proyecto practico",
                    f"{topic_clean} tutorial practico",
                    f"{topic_clean} github ejemplos",
                    f"{topic_clean} ejercicios proyectos",
                ],
            )
        )

        levels_data.append(
            PlannedLevel(
                number=5,
                title=f"Sistemas, componentes y diseño en {topic_clean}",
                objective="Estudiar arquitectura, componentes, diseño e integración",
                prerequisites=[
                    f"Aplicaciones prácticas, casos de uso y proyectos guiados de {topic_clean}"
                ],
                concepts=["Arquitectura", "Componentes", "Diseño", "Integración"],
                projects=[f"Diseño e integración aplicado a {topic_clean}"],
                queries=[
                    f"{topic_clean} arquitectura",
                    f"{topic_clean} diseño",
                    f"{topic_clean} componentes",
                    f"{topic_clean} libro tecnico",
                    f"{topic_clean} manual tecnico",
                    f"{topic_clean} referencias tecnicas",
                ],
            )
        )

        levels_data.append(
            PlannedLevel(
                number=6,
                title=f"Análisis, verificación y optimización de {topic_clean}",
                objective="Analizar, verificar, optimizar y resolver problemas complejos",
                prerequisites=[f"Sistemas, componentes y diseño en {topic_clean}"],
                concepts=["Análisis", "Verificación", "Optimización", "Validación"],
                projects=[f"Proyecto intermedio con análisis en {topic_clean}"],
                queries=[
                    f"{topic_clean} analisis",
                    f"{topic_clean} optimizacion",
                    f"{topic_clean} ejercicios avanzados",
                    f"{topic_clean} problemas resueltos",
                    f"{topic_clean} tutoriales avanzados",
                    f"{topic_clean} proyectos intermedios",
                ],
            )
        )

        if depth >= 7:
            levels_data.append(
                PlannedLevel(
                    number=7,
                    title=f"Proyectos integradores complejos en {topic_clean}",
                    objective="Desarrollar proyecto integrador con múltiples elementos",
                    prerequisites=[f"Análisis, verificación y optimización de {topic_clean}"],
                    concepts=["Integración", "Documentación técnica", "Pruebas"],
                    projects=[f"Proyecto integrador completo y documentado de {topic_clean}"],
                    queries=[
                        f"{topic_clean} proyecto integrador",
                        f"{topic_clean} proyecto completo",
                        f"{topic_clean} github repositorio",
                        f"{topic_clean} ejemplos completos",
                        f"{topic_clean} practica avanzada",
                        f"{topic_clean} casos reales",
                    ],
                )
            )

        if depth >= 8:
            levels_data.append(
                PlannedLevel(
                    number=8,
                    title=f"Temas avanzados, especialización y bibliografía en {topic_clean}",
                    objective="Explorar temas avanzados, estándares y bibliografía especializada",
                    prerequisites=[f"Proyectos integradores complejos en {topic_clean}"],
                    concepts=["Temas avanzados", "Estándares", "Bibliografía especializada"],
                    projects=[f"Proyecto de especialización con referencias en {topic_clean}"],
                    queries=[
                        f"{topic_clean} avanzado",
                        f"{topic_clean} handbook",
                        f"{topic_clean} referencias tecnicas",
                        f"{topic_clean} libros avanzados",
                        f"{topic_clean} papers",
                        f"{topic_clean} survey",
                    ],
                )
            )

        if depth >= 9:
            levels_data.append(
                PlannedLevel(
                    number=9,
                    title=f"Estado del arte, investigación y tendencias en {topic_clean}",
                    objective="Revisar estado del arte, papers y tendencias actuales",
                    prerequisites=[
                        f"Temas avanzados, especialización y bibliografía en {topic_clean}"
                    ],
                    concepts=["Estado del arte", "Investigación", "Tendencias"],
                    projects=[f"Revisión bibliográfica y propuesta aplicada en {topic_clean}"],
                    queries=[
                        f"{topic_clean} estado del arte",
                        f"{topic_clean} review",
                        f"{topic_clean} survey paper",
                        f"{topic_clean} recent research",
                        f"{topic_clean} tendencias",
                        f"{topic_clean} papers cientificos",
                    ],
                )
            )

        if depth >= 10:
            levels_data.append(
                PlannedLevel(
                    number=10,
                    title=f"Maestría práctica, innovación y proyecto final en {topic_clean}",
                    objective="Sintetizar, innovar y entregar proyecto original documentado",
                    prerequisites=[f"Estado del arte, investigación y tendencias en {topic_clean}"],
                    concepts=["Síntesis", "Innovación", "Documentación profesional"],
                    projects=[
                        f"Proyecto original completo con documentación profesional en {topic_clean}"
                    ],
                    queries=[
                        f"{topic_clean} proyecto original",
                        f"{topic_clean} recursos completos",
                        f"{topic_clean} bibliografia completa",
                        f"{topic_clean} github avanzado",
                        f"{topic_clean} casos avanzados",
                        f"{topic_clean} material completo",
                    ],
                )
            )

        return PlannedRoadmap(topic=topic_clean, levels=levels_data)


class LLMPlanner:
    """Planificador basado en un proveedor LLM."""

    def __init__(self, provider: LLMProvider | None = None, use_llm: bool = False) -> None:
        self.provider = provider
        self.use_llm = use_llm
        self._heuristic = HeuristicPlanner()

    async def plan(self, topic: str, depth: int) -> PlannedRoadmap:
        """Genera el plan usando heurístico por defecto."""
        if self.use_llm and self.provider is not None:
            try:
                logger.info("LLM planner solicitado pero usando heurístico por seguridad")
            except Exception as exc:
                logger.warning("LLM planner falló, usando heurístico: %s", exc)

        return await self._heuristic.plan(topic, depth)


__all__ = ["HeuristicPlanner", "LLMPlanner", "PlannedLevel", "PlannedRoadmap", "Planner"]
