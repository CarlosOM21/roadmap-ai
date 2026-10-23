"""Ranking determinista de recursos (Fase 3)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from roadmap_ai.models import Resource, ResourceType

logger = logging.getLogger(__name__)


@runtime_checkable
class Ranker(Protocol):
    """Contrato del ranking heurístico independiente del LLM."""

    def rank(
        self,
        resources: Sequence[Resource],
        topic: str,
        level_title: str,
    ) -> list[Resource]:
        """Devuelve recursos ordenados por relevancia."""
        ...


class HeuristicRanker:
    """Ranker basado en reglas heurísticas deterministas."""

    def rank(
        self,
        resources: Sequence[Resource],
        topic: str,
        level_title: str,
    ) -> list[Resource]:
        """Calcula relevancia heurística y ordena los recursos."""
        if not resources:
            return []

        topic_lower = topic.lower()
        level_lower = level_title.lower()
        scored_resources = []

        for resource in resources:
            score = 0.0
            title_lower = resource.title.lower()
            summary_lower = resource.summary.lower()

            # Coincidencia con tema (peso alto)
            if topic_lower in title_lower:
                score += 0.25
            elif any(word in title_lower for word in topic_lower.split() if len(word) > 3):
                score += 0.12

            if topic_lower in summary_lower:
                score += 0.08
            elif any(word in summary_lower for word in topic_lower.split() if len(word) > 3):
                score += 0.04

            # Coincidencia con nivel (peso medio)
            if level_lower in title_lower:
                score += 0.15
            elif any(word in title_lower for word in level_lower.split() if len(word) > 3):
                score += 0.08

            if level_lower in summary_lower:
                score += 0.04

            # Preferencia por open access
            if resource.open_access:
                score += 0.12

            # Preferencia por recencia (papers/libros recientes)
            if resource.year:
                if resource.year >= 2020:
                    score += 0.08
                elif resource.year >= 2015:
                    score += 0.05
                elif resource.year >= 2010:
                    score += 0.03

            # Preferencia por citas (si disponible)
            if resource.citation_count and resource.citation_count > 0:
                # Logarítmico para evitar sesgo excesivo
                import math

                citation_score = min(0.08, math.log10(resource.citation_count + 1) * 0.04)
                score += citation_score

            # Preferencia por tipo de recurso según contexto
            if resource.type == ResourceType.PAPER and "fundamentos" in level_lower:
                score += 0.05
            elif resource.type == ResourceType.BOOK and (
                "intro" in level_lower or "fundamentos" in level_lower
            ):
                score += 0.05
            elif resource.type == ResourceType.VIDEO and (
                "practica" in level_lower or "aplicacion" in level_lower
            ):
                score += 0.05
            elif resource.type == ResourceType.DOCUMENTATION:
                score += 0.02

            # Bonus por tener autores y metadata completa
            if resource.authors:
                score += 0.02
            if resource.doi:
                score += 0.03

            # Normalizar a [0,1]
            score = min(1.0, max(0.0, score))

            # Crear copia con relevance_score actualizado
            resource_dict = resource.model_dump()
            resource_dict["relevance_score"] = round(score, 4)
            try:
                scored_resource = Resource.model_validate(resource_dict)
                scored_resources.append(scored_resource)
            except Exception:
                scored_resources.append(resource)

        # Ordenar por relevance_score descendente
        scored_resources.sort(key=lambda r: r.relevance_score, reverse=True)
        return scored_resources


__all__ = ["HeuristicRanker", "Ranker"]
