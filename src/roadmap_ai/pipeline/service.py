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
from roadmap_ai.storage.database import Database
from roadmap_ai.storage.repositories import RoadmapRepository

logger = logging.getLogger(__name__)


class PipelineService:
    """Orquesta planner, retriever, ranker y builder."""

    def __init__(
        self,
        database: Database,
        settings: Settings | None = None,
        use_llm: bool = False,
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
        """Obtiene instancias de fuentes configuradas."""
        all_sources = [
            OpenAlexSource(self.settings) if self.settings else OpenAlexSource(),
            SemanticScholarSource(self.settings) if self.settings else SemanticScholarSource(),
            ArxivSource(self.settings) if self.settings else ArxivSource(),
            OpenLibrarySource(self.settings) if self.settings else OpenLibrarySource(),
            YouTubeSource(self.settings) if self.settings else YouTubeSource(),
        ]

        if source_names is None:
            return all_sources

        source_map = {s.name: s for s in all_sources}
        return [source_map[name] for name in source_names if name in source_map]

    async def generate(
        self,
        topic: str,
        depth: int = 8,
        max_resources: int = 120,
        source_names: list[str] | None = None,
        offline: bool = False,
    ) -> Roadmap:
        """Genera roadmap completo usando el pipeline."""
        if offline:
            from roadmap_ai.sample_data import build_sample_roadmap

            logger.info("Modo offline: usando datos de demostración")
            return build_sample_roadmap(topic, depth=depth, max_resources=max_resources)

        # 1. Planificar
        logger.info("Planificando roadmap para: %s", topic)
        planned = await self.planner.plan(topic, depth)

        # 2. Obtener todas las queries
        all_queries = []
        for level in planned.levels:
            all_queries.extend(level.queries)
        # Añadir queries genéricas y diversas sin sesgo a dominio
        all_queries.insert(0, topic)
        all_queries.append(f"{topic} curso")
        all_queries.append(f"{topic} libro")
        all_queries.append(f"{topic} tutorial")
        all_queries.append(f"{topic} ejercicios")
        all_queries.append(f"{topic} proyectos")
        all_queries.append(f"{topic} github")
        all_queries.append(f"{topic} papers")
        all_queries.append(f"{topic} referencias")
        # Eliminar duplicados manteniendo orden
        unique_queries = []
        seen_q = set()
        for q in all_queries:
            q_lower = q.lower().strip()
            if q_lower not in seen_q and q_lower:
                unique_queries.append(q)
                seen_q.add(q_lower)

        # 3. Recuperar recursos
        logger.info("Recuperando recursos con %d queries", len(unique_queries))
        sources = self._get_sources(source_names)
        source_results = await self.retriever.retrieve(
            unique_queries, sources, limit=max(15, max_resources // len(sources) + 15)
        )

        # Recopilar todos los recursos
        all_resources = []
        for sr in source_results:
            if sr.success:
                all_resources.extend(sr.resources)

        if not all_resources:
            logger.warning("No se encontraron recursos, usando datos de demostración")
            from roadmap_ai.sample_data import build_sample_roadmap

            return build_sample_roadmap(topic, depth=depth, max_resources=max_resources)

        # 4. Construir roadmap
        logger.info("Construyendo roadmap con %d recursos", len(all_resources))
        resources_per_level = max(8, max_resources // len(planned.levels))
        roadmap = await self.builder.build(
            planned,
            all_resources,
            max_resources_per_level=resources_per_level,
            total_max_resources=max_resources,
        )

        return roadmap


__all__ = ["PipelineService"]
