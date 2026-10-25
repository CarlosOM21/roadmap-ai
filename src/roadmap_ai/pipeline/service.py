"""Servicio orquestador del pipeline completo (Fase 3)."""

from __future__ import annotations

import logging

from roadmap_ai.config import Settings
from roadmap_ai.models import Roadmap
from roadmap_ai.pipeline.builder import DefaultRoadmapBuilder
from roadmap_ai.pipeline.planner import HeuristicPlanner
from roadmap_ai.pipeline.ranker import HeuristicRanker
from roadmap_ai.pipeline.retriever import MultiSourceRetriever
from roadmap_ai.sources.arxiv import ArxivSource
from roadmap_ai.sources.base import Source
from roadmap_ai.sources.open_library import OpenLibrarySource
from roadmap_ai.sources.openalex import OpenAlexSource
from roadmap_ai.sources.semantic_scholar import SemanticScholarSource
from roadmap_ai.sources.youtube import YouTubeSource
from roadmap_ai.sources.github import GitHubSource
from roadmap_ai.storage.database import Database
from roadmap_ai.storage.repositories import RoadmapRepository

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(
        self, database: Database, settings: Settings | None = None, use_llm: bool = False
    ) -> None:
        self.database = database
        self.settings = settings
        self.use_llm = use_llm
        self.planner = HeuristicPlanner()
        self.retriever = MultiSourceRetriever(database)
        self.ranker = HeuristicRanker()
        self.repository = RoadmapRepository(database)
        self.builder = DefaultRoadmapBuilder(self.repository)

    def _get_sources(self, source_names: list[str] | None = None) -> list[Source]:
        all_sources = [
            OpenLibrarySource(self.settings) if self.settings else OpenLibrarySource(),
            GitHubSource(self.settings) if self.settings else GitHubSource(),
            YouTubeSource(self.settings) if self.settings else YouTubeSource(),
            OpenAlexSource(self.settings) if self.settings else OpenAlexSource(),
            SemanticScholarSource(self.settings) if self.settings else SemanticScholarSource(),
            ArxivSource(self.settings) if self.settings else ArxivSource(),
        ]
        if source_names is None:
            return all_sources
        source_map = {s.name: s for s in all_sources}
        return [source_map[name] for name in source_names if name in source_map]

    async def generate(
        self,
        topic: str,
        depth: int = 8,
        max_resources: int = 200,
        source_names: list[str] | None = None,
        offline: bool = False,
    ) -> Roadmap:
        if offline:
            from roadmap_ai.sample_data import build_sample_roadmap

            logger.info("Modo offline: usando datos de demostración")
            return build_sample_roadmap(topic, depth=depth, max_resources=max_resources)

        logger.info("Planificando roadmap para: %s", topic)
        planned = await self.planner.plan(topic, depth)

        all_queries = []
        for level in planned.levels:
            all_queries.extend(level.queries)
        all_queries.insert(0, topic)
        all_queries.append(f"{topic} curso")
        all_queries.append(f"{topic} tutorial")
        all_queries.append(f"{topic} ejercicios")
        all_queries.append(f"{topic} practicas")
        all_queries.append(f"{topic} proyecto")
        all_queries.append(f"{topic} github")
        all_queries.append(f"{topic} repositorio")
        all_queries.append(f"{topic} youtube")
        all_queries.append(f"{topic} manual")
        all_queries.append(f"{topic} libro")
        all_queries.append(f"{topic} papers")

        unique_queries = []
        seen_q = set()
        for q in all_queries:
            q_lower = q.lower().strip()
            if q_lower not in seen_q and q_lower:
                unique_queries.append(q)
                seen_q.add(q_lower)

        logger.info("Recuperando recursos con %d queries", len(unique_queries))
        sources = self._get_sources(source_names)
        source_results = await self.retriever.retrieve(
            unique_queries, sources, limit=max(10, max_resources // max(1, len(sources)) + 15)
        )

        all_resources = []
        for sr in source_results:
            if sr.success:
                all_resources.extend(sr.resources)

        # Si solo hay papers (fallaron otras fuentes), intentar forzar más diversidad con consultas específicas
        from collections import Counter

        types = Counter([r.type.value for r in all_resources])
        if (
            types
            and types.get("paper", 0) == len(all_resources)
            and len(all_resources) < max_resources
        ):
            try:
                extra_queries = [
                    f"{topic} tutorial",
                    f"{topic} curso",
                    f"{topic} libro",
                    f"{topic} github",
                    f"{topic} ejemplos",
                    f"{topic} ejercicios",
                ]
                extra_sources = []
                for s in sources:
                    if getattr(s, "name") in ["open_library", "github", "youtube"]:
                        extra_sources.append(s)
                if extra_sources:
                    extra_results = await self.retriever.retrieve(
                        extra_queries, extra_sources, limit=20
                    )
                    for sr in extra_results:
                        if sr.success:
                            all_resources.extend(sr.resources)
            except Exception:
                pass

        if not all_resources:
            logger.warning("No se encontraron recursos, usando datos de demostración")
            from roadmap_ai.sample_data import build_sample_roadmap

            return build_sample_roadmap(topic, depth=depth, max_resources=max_resources)

        logger.info("Construyendo roadmap con %d recursos", len(all_resources))
        resources_per_level = max(18, max_resources // max(1, len(planned.levels)))
        roadmap = await self.builder.build(
            planned,
            all_resources,
            max_resources_per_level=resources_per_level,
            total_max_resources=max_resources,
        )
        return roadmap


__all__ = ["PipelineService"]
