"""Planificación curricular preliminar (Fase 3)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from roadmap_ai.llm.provider import LLMProvider


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


class LLMPlanner:
    """Planificador basado en un proveedor LLM.

    La implementación completa corresponde a la Fase 3.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def plan(self, topic: str, depth: int) -> PlannedRoadmap:
        """Genera el plan; pendiente de implementación."""
        raise NotImplementedError("El planner se implementa en la Fase 3")


__all__ = ["LLMPlanner", "PlannedLevel", "PlannedRoadmap", "Planner"]
