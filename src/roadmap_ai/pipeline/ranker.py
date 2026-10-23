"""Ranking determinista de recursos (Fase 3)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from roadmap_ai.models import Resource


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
    """Ranker basado en reglas; se implementará en la Fase 3."""

    def rank(
        self,
        resources: Sequence[Resource],
        topic: str,
        level_title: str,
    ) -> list[Resource]:
        """Calcula relevancia; pendiente de implementación."""
        raise NotImplementedError("El ranker se implementa en la Fase 3")


__all__ = ["HeuristicRanker", "Ranker"]
