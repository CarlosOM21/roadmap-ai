"""Construcción del roadmap final y persistencia (Fase 3)."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from roadmap_ai.models import Resource, Roadmap, RoadmapLevel, utc_now
from roadmap_ai.pipeline.planner import PlannedRoadmap
from roadmap_ai.pipeline.ranker import HeuristicRanker
from roadmap_ai.storage.repositories import RoadmapRepository

logger = logging.getLogger(__name__)


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


class DefaultRoadmapBuilder:
    """Constructor heurístico que asigna recursos rankeados a niveles."""

    def __init__(self, repository: RoadmapRepository | None = None) -> None:
        self.repository = repository
        self.ranker = HeuristicRanker()

    async def build(
        self,
        planned: PlannedRoadmap,
        resources: list[Resource],
        max_resources_per_level: int = 12,
        total_max_resources: int = 80,
    ) -> Roadmap:
        """Construye roadmap válido asignando recursos a cada nivel."""
        if not resources:
            raise ValueError("No hay recursos disponibles para construir el roadmap")

        # Rankear todos los recursos por relevancia global
        ranked_resources = self.ranker.rank(resources, planned.topic, planned.topic)

        # Limitar recursos totales
        ranked_resources = ranked_resources[:total_max_resources]

        # Asignar recursos a cada nivel
        roadmap_levels = []
        resources_per_level = max(8, max_resources_per_level)

        for planned_level in planned.levels:
            # Rankear recursos específicamente para este nivel
            level_resources = self.ranker.rank(ranked_resources, planned.topic, planned_level.title)

            # Tomar top recursos para este nivel (evitando duplicados excesivos)
            assigned = []
            seen_ids = set()
            for res in level_resources:
                if res.id in seen_ids:
                    continue
                assigned.append(res)
                seen_ids.add(res.id)
                if len(assigned) >= resources_per_level:
                    break

            if len(assigned) < resources_per_level:
                for res in ranked_resources:
                    if res.id in seen_ids:
                        continue
                    assigned.append(res)
                    seen_ids.add(res.id)
                    if len(assigned) >= resources_per_level:
                        break

            roadmap_level = RoadmapLevel(
                number=planned_level.number,
                title=planned_level.title,
                objective=planned_level.objective,
                prerequisites=planned_level.prerequisites,
                concepts=planned_level.concepts,
                projects=planned_level.projects,
                resources=assigned,
            )
            roadmap_levels.append(roadmap_level)

        # Recopilar todos los recursos únicos del roadmap
        all_resources_dict = {}
        for level in roadmap_levels:
            for res in level.resources:
                all_resources_dict[res.id] = res

        # Crear título y descripción
        title = f"Roadmap de {planned.topic}"
        description = (
            f"Ruta de aprendizaje progresiva para dominar {planned.topic}, "
            f"con {len(roadmap_levels)} niveles y recursos académicos verificables."
        )

        roadmap = Roadmap(
            topic=planned.topic,
            title=title,
            description=description,
            levels=roadmap_levels,
            resources=list(all_resources_dict.values()),
            queries_used=[query for level in planned.levels for query in level.queries],
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        # Persistir si hay repositorio
        if self.repository is not None:
            try:
                self.repository.save(roadmap)
                logger.info("Roadmap %s guardado en base de datos", roadmap.id)
            except Exception as exc:
                logger.error("Error guardando roadmap: %s", exc)
                raise

        return roadmap


class LLMRoadmapBuilder:
    """Constructor asistido por LLM; usa builder por defecto por seguridad."""

    def __init__(self, repository: RoadmapRepository | None = None) -> None:
        self.repository = repository
        self._builder = DefaultRoadmapBuilder(repository)

    async def build(
        self,
        planned: PlannedRoadmap,
        resources: list[Resource],
        max_resources_per_level: int = 6,
        total_max_resources: int = 30,
    ) -> Roadmap:
        """Construye y guarda el roadmap."""
        # LLM solo puede organizar/redactar, nunca inventar recursos
        return await self._builder.build(
            planned, resources, max_resources_per_level, total_max_resources
        )


__all__ = ["DefaultRoadmapBuilder", "LLMRoadmapBuilder", "RoadmapBuilder"]
