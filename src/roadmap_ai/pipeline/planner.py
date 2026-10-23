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
    levels: list[PlannedLevel] = Field(min_length=4, max_length=6)


@runtime_checkable
class Planner(Protocol):
    """Contrato del planificador curricular."""

    async def plan(self, topic: str, depth: int) -> PlannedRoadmap:
        """Genera una estructura de niveles y queries de búsqueda."""
        ...


class HeuristicPlanner:
    """Planificador heurístico determinista sin LLM."""

    async def plan(self, topic: str, depth: int) -> PlannedRoadmap:
        """Genera plan curricular basado en reglas heurísticas."""
        depth = max(4, min(6, depth))
        topic_clean = topic.strip()

        # Plantillas heurísticas por tipo de tema
        levels_data = []

        if depth >= 4:
            levels_data.append(
                PlannedLevel(
                    number=1,
                    title=f"Fundamentos de {topic_clean}",
                    objective=f"Comprender los conceptos básicos y terminología de {topic_clean}",
                    prerequisites=[],
                    concepts=["Conceptos básicos", "Terminología", "Historia y contexto"],
                    projects=[f"Mapa conceptual de {topic_clean}"],
                    queries=[
                        f"introduccion {topic_clean}",
                        f"fundamentos {topic_clean} libro",
                        f"{topic_clean} conceptos basicos",
                    ],
                )
            )

        if depth >= 5:
            levels_data.append(
                PlannedLevel(
                    number=2,
                    title=f"Teoría y principios de {topic_clean}",
                    objective="Dominar los principios teóricos fundamentales",
                    prerequisites=[f"Fundamentos de {topic_clean}"],
                    concepts=["Principios", "Leyes", "Modelos teóricos"],
                    projects=[f"Resolución de ejercicios teóricos de {topic_clean}"],
                    queries=[
                        f"teoria {topic_clean}",
                        f"principios {topic_clean}",
                        f"{topic_clean} fundamentos teoricos",
                    ],
                )
            )
        else:
            levels_data.append(
                PlannedLevel(
                    number=2,
                    title=f"Teoría y fundamentos avanzados de {topic_clean}",
                    objective="Profundizar en los aspectos teóricos",
                    prerequisites=[f"Fundamentos de {topic_clean}"],
                    concepts=["Teoría", "Análisis", "Modelado"],
                    projects=[f"Análisis teórico aplicado a {topic_clean}"],
                    queries=[
                        f"teoria {topic_clean} avanzado",
                        f"{topic_clean} analisis",
                    ],
                )
            )

        if depth >= 5:
            levels_data.append(
                PlannedLevel(
                    number=3,
                    title=f"Herramientas y metodologías de {topic_clean}",
                    objective="Aprender las herramientas y métodos prácticos",
                    prerequisites=[f"Teoría y principios de {topic_clean}"],
                    concepts=["Herramientas", "Metodologías", "Técnicas"],
                    projects=[f"Aplicación práctica con herramientas de {topic_clean}"],
                    queries=[
                        f"{topic_clean} herramientas",
                        f"{topic_clean} metodologia practica",
                        f"tutorial {topic_clean}",
                    ],
                )
            )
        else:
            levels_data.append(
                PlannedLevel(
                    number=3,
                    title=f"Aplicaciones prácticas de {topic_clean}",
                    objective="Aplicar conocimientos a casos prácticos",
                    prerequisites=[f"Teoría y fundamentos avanzados de {topic_clean}"],
                    concepts=["Aplicaciones", "Casos de uso", "Implementación"],
                    projects=[f"Proyecto práctico de {topic_clean}"],
                    queries=[
                        f"{topic_clean} aplicaciones practicas",
                        f"{topic_clean} casos de uso",
                    ],
                )
            )

        levels_data.append(
            PlannedLevel(
                number=4,
                title=f"Proyectos y casos reales en {topic_clean}",
                objective="Resolver problemas reales mediante proyectos integradores",
                prerequisites=[f"Herramientas y metodologías de {topic_clean}"]
                if depth >= 5
                else [f"Aplicaciones prácticas de {topic_clean}"],
                concepts=["Proyectos integradores", "Resolución de problemas", "Buenas prácticas"],
                projects=[f"Proyecto integrador completo de {topic_clean}"],
                queries=[
                    f"{topic_clean} proyecto practico",
                    f"{topic_clean} ejemplos reales",
                    f"ejercicios {topic_clean}",
                ],
            )
        )

        if depth >= 5:
            levels_data.append(
                PlannedLevel(
                    number=5,
                    title=f"Temas avanzados y especialización en {topic_clean}",
                    objective="Explorar temas avanzados y áreas de especialización",
                    prerequisites=[f"Proyectos y casos reales en {topic_clean}"],
                    concepts=["Temas avanzados", "Investigación", "Tendencias"],
                    projects=[f"Investigación o proyecto de especialización en {topic_clean}"],
                    queries=[
                        f"{topic_clean} avanzado",
                        f"{topic_clean} investigacion",
                        f"{topic_clean} temas avanzados",
                    ],
                )
            )

        if depth == 6:
            levels_data.append(
                PlannedLevel(
                    number=6,
                    title=f"Maestría y dominio experto de {topic_clean}",
                    objective="Desarrollar capacidad crítica y visión experta",
                    prerequisites=[f"Temas avanzados y especialización en {topic_clean}"],
                    concepts=["Síntesis", "Crítica", "Innovación"],
                    projects=[f"Propuesta innovadora o contribución original en {topic_clean}"],
                    queries=[
                        f"{topic_clean} estado del arte",
                        f"{topic_clean} investigacion avanzada",
                    ],
                )
            )

        return PlannedRoadmap(topic=topic_clean, levels=levels_data)


class LLMPlanner:
    """Planificador basado en un proveedor LLM.

    Usa heurístico como fallback si LLM no está disponible.
    """

    def __init__(self, provider: LLMProvider | None = None, use_llm: bool = False) -> None:
        self.provider = provider
        self.use_llm = use_llm
        self._heuristic = HeuristicPlanner()

    async def plan(self, topic: str, depth: int) -> PlannedRoadmap:
        """Genera el plan usando LLM si está disponible, sino heurístico."""
        if self.use_llm and self.provider is not None:
            try:
                # Por ahora usamos heurístico; implementación LLM vendrá después
                # Respetando regla: LLM nunca inventa recursos
                logger.info("LLM planner solicitado pero usando heurístico por seguridad")
            except Exception as exc:
                logger.warning("LLM planner falló, usando heurístico: %s", exc)

        return await self._heuristic.plan(topic, depth)


__all__ = ["HeuristicPlanner", "LLMPlanner", "PlannedLevel", "PlannedRoadmap", "Planner"]
