"""Construcción del roadmap final y persistencia (Fase 3)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from roadmap_ai.models import Resource, Roadmap
from roadmap_ai.pipeline.planner import PlannedRoadmap
from roadmap_ai.storage.repositories import RoadmapRepository


@runtime_checkable
class RoadmapBuilder(Protocol):
    """Contrato del constructor de roadmaps finales."""

    async def build(
        self,
        planned: PlannedRoadmap,
        resources: list[Resource],
    ) -> Roadmap:
        """Asigna recursos y produce un roadmap validado."""
        ...


class LLMRoadmapBuilder:
    """Constructor asistido por LLM; se implementará en la Fase 3."""

    def __init__(self, repository: RoadmapRepository) -> None:
        self.repository = repository

    async def build(
        self,
        planned: PlannedRoadmap,
        resources: list[Resource],
    ) -> Roadmap:
        """Construye y guarda el roadmap; pendiente de implementación."""
        raise NotImplementedError("El builder se implementa en la Fase 3")


__all__ = ["LLMRoadmapBuilder", "RoadmapBuilder"]
