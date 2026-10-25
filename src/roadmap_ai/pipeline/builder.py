"""Construcción del roadmap final y persistencia (Fase 3)."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from roadmap_ai.models import Resource, Roadmap, RoadmapLevel
from roadmap_ai.pipeline.planner import PlannedRoadmap
from roadmap_ai.pipeline.ranker import HeuristicRanker
from roadmap_ai.storage.repositories import RoadmapRepository

logger = logging.getLogger(__name__)


@runtime_checkable
class RoadmapBuilder(Protocol):
    async def build(self, planned: PlannedRoadmap, resources: list[Resource]) -> Roadmap: ...


class DefaultRoadmapBuilder:
    def __init__(self, repository: RoadmapRepository | None = None) -> None:
        self.repository = repository
        self.ranker = HeuristicRanker()

    async def build(
        self,
        planned: PlannedRoadmap,
        resources: list[Resource],
        max_resources_per_level: int = 22,
        total_max_resources: int = 220,
    ) -> Roadmap:
        if not resources:
            raise ValueError("No hay recursos disponibles para construir el roadmap")

        ranked_resources = self.ranker.rank(resources, planned.topic, planned.topic)
        ranked_resources = ranked_resources[:total_max_resources]

        roadmap_levels = []
        resources_per_level = max(18, max_resources_per_level)
        global_seen = set()

        for planned_level in planned.levels:
            level_title_lower = planned_level.title.lower()
            level_resources = self.ranker.rank(ranked_resources, planned.topic, planned_level.title)

            assigned = []
            seen_ids = set()

            preferred_types = []
            if (
                "fundamento" in level_title_lower
                or "historia" in level_title_lower
                or "base" in level_title_lower
                or "intro" in level_title_lower
            ):
                preferred_types = ["book", "course", "documentation", "video"]
            elif (
                "practica" in level_title_lower
                or "proyecto" in level_title_lower
                or "aplicacion" in level_title_lower
                or "integrador" in level_title_lower
                or "caso" in level_title_lower
                or "laboratorio" in level_title_lower
            ):
                preferred_types = ["video", "course", "documentation", "tool", "book"]
            elif (
                "diseño" in level_title_lower
                or "componente" in level_title_lower
                or "arquitectura" in level_title_lower
                or "analisis" in level_title_lower
                or "transmision" in level_title_lower
                or "mecanismo" in level_title_lower
                or "engran" in level_title_lower
                or "eje" in level_title_lower
            ):
                preferred_types = ["book", "documentation", "video", "course"]
            elif (
                "control" in level_title_lower
                or "pid" in level_title_lower
                or "automat" in level_title_lower
                or "sensor" in level_title_lower
                or "actuador" in level_title_lower
            ):
                preferred_types = ["book", "documentation", "video", "course", "tool"]
            elif (
                "investig" in level_title_lower
                or "estado del arte" in level_title_lower
                or "research" in level_title_lower
                or "review" in level_title_lower
            ):
                preferred_types = ["paper", "book", "documentation", "course"]
            else:
                preferred_types = ["book", "video", "course", "documentation", "paper"]

            for ptype in preferred_types:
                for res in level_resources:
                    if res.id in seen_ids or res.id in global_seen:
                        continue
                    if res.type.value == ptype:
                        assigned.append(res)
                        seen_ids.add(res.id)
                        global_seen.add(res.id)
                        if len(assigned) >= resources_per_level:
                            break
                if len(assigned) >= resources_per_level:
                    break

            if len(assigned) < resources_per_level:
                for res in level_resources:
                    if res.id in seen_ids or res.id in global_seen:
                        continue
                    assigned.append(res)
                    seen_ids.add(res.id)
                    global_seen.add(res.id)
                    if len(assigned) >= resources_per_level:
                        break

            # Try to ensure variety by type if possible
            if len(assigned) < resources_per_level:
                types_present = {r.type.value for r in assigned}
                for desired in ["book", "video", "course", "documentation", "tool", "paper"]:
                    if desired in types_present:
                        continue
                    for res in ranked_resources:
                        if res.id in seen_ids or res.id in global_seen:
                            continue
                        if res.type.value == desired:
                            assigned.append(res)
                            seen_ids.add(res.id)
                            global_seen.add(res.id)
                            types_present.add(desired)
                            if len(assigned) >= resources_per_level:
                                break
                    if len(assigned) >= resources_per_level:
                        break

            if len(assigned) < resources_per_level:
                for res in ranked_resources:
                    if res.id in seen_ids or res.id in global_seen:
                        continue
                    assigned.append(res)
                    seen_ids.add(res.id)
                    global_seen.add(res.id)
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

        all_resources_dict = {}
        for level in roadmap_levels:
            for res in level.resources:
                all_resources_dict[res.id] = res

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
            created_at=__import__("roadmap_ai.models", fromlist=["utc_now"]).utc_now(),
            updated_at=__import__("roadmap_ai.models", fromlist=["utc_now"]).utc_now(),
        )

        if self.repository is not None:
            try:
                self.repository.save(roadmap)
                logger.info("Roadmap %s guardado en base de datos", roadmap.id)
            except Exception as exc:
                logger.error("Error guardando roadmap: %s", exc)
                raise

        return roadmap


class LLMRoadmapBuilder:
    def __init__(self, repository: RoadmapRepository | None = None) -> None:
        self.repository = repository
        self._builder = DefaultRoadmapBuilder(repository)

    async def build(
        self,
        planned: PlannedRoadmap,
        resources: list[Resource],
        max_resources_per_level: int = 22,
        total_max_resources: int = 220,
    ) -> Roadmap:
        return await self._builder.build(
            planned, resources, max_resources_per_level, total_max_resources
        )


__all__ = ["DefaultRoadmapBuilder", "LLMRoadmapBuilder", "RoadmapBuilder"]
