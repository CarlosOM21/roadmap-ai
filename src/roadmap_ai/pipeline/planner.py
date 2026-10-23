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
        """Genera plan curricular amplio y diverso."""
        depth = max(6, min(8, depth))  # Más robusto por defecto
        topic_clean = topic.strip()

        levels_data = []

        levels_data.append(
            PlannedLevel(
                number=1,
                title=f"Fundamentos, historia y panorama de {topic_clean}",
                objective=f"Comprender conceptos y terminología de {topic_clean}",
                prerequisites=[],
                concepts=[
                    "Conceptos básicos",
                    "Terminología",
                    "Historia",
                    "Aplicaciones",
                    "Áreas afines",
                ],
                projects=[f"Mapa conceptual completo de {topic_clean}"],
                queries=[
                    f"introduccion {topic_clean}",
                    f"fundamentos {topic_clean} libro",
                    f"{topic_clean} conceptos basicos",
                    f"{topic_clean} curso introductorio",
                    f"historia {topic_clean}",
                ],
            )
        )

        levels_data.append(
            PlannedLevel(
                number=2,
                title=f"Matemáticas, lógica y bases teóricas para {topic_clean}",
                objective="Dominar las bases matemáticas y lógicas necesarias",
                prerequisites=[f"Fundamentos, historia y panorama de {topic_clean}"],
                concepts=["Matemáticas", "Lógica", "Probabilidad", "Álgebra", "Estadística"],
                projects=[f"Ejercicios matemáticos aplicados a {topic_clean}"],
                queries=[
                    f"{topic_clean} matematicas",
                    f"probabilidad {topic_clean}",
                    f"logica {topic_clean}",
                    f"estadistica {topic_clean}",
                    f"{topic_clean} bases teoricas libro",
                ],
            )
        )

        levels_data.append(
            PlannedLevel(
                number=3,
                title=f"Algoritmos, búsqueda, heurísticas y razonamiento en {topic_clean}",
                objective="Aprender algoritmos, búsqueda y heurísticas",
                prerequisites=[f"Matemáticas, lógica y bases teóricas para {topic_clean}"],
                concepts=[
                    "Algoritmos de búsqueda",
                    "Búsqueda heurística",
                    "Juegos",
                    "Razonamiento",
                    "Satisfacción de restricciones",
                ],
                projects=[f"Implementar algoritmos para {topic_clean}"],
                queries=[
                    f"algoritmos de busqueda {topic_clean}",
                    f"busqueda heuristica {topic_clean}",
                    f"heuristicas {topic_clean}",
                    f"{topic_clean} algoritmos libro",
                    f"{topic_clean} curso algoritmos",
                ],
            )
        )

        levels_data.append(
            PlannedLevel(
                number=4,
                title=f"Aprendizaje automático, clasificadores y modelos en {topic_clean}",
                objective="Dominar aprendizaje supervisado/no supervisado y clasificadores",
                prerequisites=[
                    f"Algoritmos, búsqueda, heurísticas y razonamiento en {topic_clean}"
                ],
                concepts=[
                    "Aprendizaje supervisado",
                    "Clasificadores",
                    "Validación",
                    "Features",
                    "Overfitting",
                ],
                projects=[f"Entrenar clasificadores para {topic_clean}"],
                queries=[
                    f"machine learning {topic_clean}",
                    f"clasificadores {topic_clean}",
                    f"aprendizaje supervisado {topic_clean}",
                    f"deep learning {topic_clean}",
                    f"{topic_clean} sklearn tutorial",
                    f"{topic_clean} curso machine learning",
                ],
            )
        )

        if depth >= 6:
            levels_data.append(
                PlannedLevel(
                    number=5,
                    title=f"Razonamiento bajo incertidumbre y RL en {topic_clean}",
                    objective="Aprender incertidumbre, MDPs, planificación y RL",
                    prerequisites=[
                        f"Aprendizaje automático, clasificadores y modelos en {topic_clean}"
                    ],
                    concepts=[
                        "Probabilidad bayesiana",
                        "MDP",
                        "POMDP",
                        "Aprendizaje por refuerzo",
                        "Q-Learning",
                        "Políticas",
                    ],
                    projects=[f"Resolver problemas con MDP o RL para {topic_clean}"],
                    queries=[
                        f"MDP {topic_clean}",
                        f"markov decision process {topic_clean}",
                        f"reinforcement learning {topic_clean}",
                        f"aprendizaje por refuerzo {topic_clean}",
                        f"rl tutorial {topic_clean}",
                        "pytorch reinforcement learning",
                    ],
                )
            )

        if depth >= 7:
            levels_data.append(
                PlannedLevel(
                    number=6,
                    title=f"Sistemas basados en conocimiento y RAG en {topic_clean}",
                    objective="Desarrollar agentes, PLN, conocimiento y RAG",
                    prerequisites=[f"Razonamiento bajo incertidumbre y RL en {topic_clean}"],
                    concepts=[
                        "Agentes",
                        "Ontologías",
                        "PLN",
                        "Embeddings",
                        "RAG",
                        "Sistemas conversacionales",
                    ],
                    projects=[f"Construir un agente o RAG aplicado a {topic_clean}"],
                    queries=[
                        f"agentes inteligentes {topic_clean}",
                        f"RAG {topic_clean}",
                        f"retrieval augmented generation {topic_clean}",
                        f"procesamiento lenguaje natural {topic_clean}",
                        f"nlp {topic_clean} tutorial",
                        "langchain rag tutorial",
                    ],
                )
            )

        if depth >= 8:
            levels_data.append(
                PlannedLevel(
                    number=7,
                    title=f"Ética, explicabilidad y despliegue en {topic_clean}",
                    objective="Abordar ética, sesgo, explicabilidad y MLOps",
                    prerequisites=[
                        f"Sistemas basados en conocimiento, agentes, PLN y RAG en {topic_clean}"
                    ],
                    concepts=[
                        "Ética IA",
                        "Explicabilidad",
                        "Sesgo",
                        "MLOps",
                        "Evaluación",
                        "Seguridad",
                    ],
                    projects=[f"Proyecto integral con despliegue y ética en {topic_clean}"],
                    queries=[
                        "etica inteligencia artificial",
                        f"explainable ai {topic_clean}",
                        f"mlops {topic_clean}",
                        f"{topic_clean} proyecto avanzado",
                        f"{topic_clean} papers estado del arte",
                    ],
                )
            )
            levels_data.append(
                PlannedLevel(
                    number=8,
                    title=f"Investigación, estado del arte y especialización en {topic_clean}",
                    objective="Leer estado del arte, reproducir papers y especializarse",
                    prerequisites=[f"Ética, explicabilidad y despliegue en {topic_clean}"],
                    concepts=[
                        "Revisión bibliográfica",
                        "Reproducibilidad",
                        "Investigación",
                        "Tendencias",
                        "Contribución",
                    ],
                    projects=[
                        f"Revisar estado del arte y prototipar contribución en {topic_clean}"
                    ],
                    queries=[
                        f"{topic_clean} survey paper",
                        f"{topic_clean} estado del arte",
                        f"{topic_clean} review",
                        f"{topic_clean} neurips tutorial",
                        f"{topic_clean} research papers",
                    ],
                )
            )
        elif depth == 7:
            levels_data.append(
                PlannedLevel(
                    number=7,
                    title=f"Ética, despliegue, estado del arte y especialización en {topic_clean}",
                    objective="Integrar todo con ética, despliegue y revisión bibliográfica",
                    prerequisites=[
                        f"Sistemas basados en conocimiento, agentes, PLN y RAG en {topic_clean}"
                    ],
                    concepts=["Ética", "Despliegue", "Estado del arte", "Especialización"],
                    projects=[f"Proyecto final integrador en {topic_clean}"],
                    queries=[
                        "etica inteligencia artificial",
                        f"{topic_clean} estado del arte",
                        f"{topic_clean} proyecto integrador",
                        f"{topic_clean} papers avanzados",
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
