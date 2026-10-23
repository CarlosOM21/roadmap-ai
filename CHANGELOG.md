# Changelog

Todos los cambios notables de este proyecto se documentarán en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/)
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Añadido
- **Fase 3 - Pipeline completo**: Implementación de `MultiSourceRetriever`, `HeuristicPlanner`, `HeuristicRanker`, `DefaultRoadmapBuilder` y `PipelineService` para generar roadmaps con recursos reales.
- **Integración CLI**: `roadmap generate` ahora usa el pipeline real por defecto, con fallback a datos de demostración. Nuevos flags `--offline` y `--sources` (filtrado de conectores).
- **Módulo pipeline.service**: Orquestador que conecta planner, retriever, ranker y builder.
- **Deduplicación global**: Deduplicación por URL normalizada, DOI y título en el retriever.
- **Ranking heurístico**: Scoring determinista basado en relevancia, open access, recencia, citas y tipo de recurso.

### Cambiado
- `roadmap generate` actualizado para usar pipeline real (Fase 3). Mensajes actualizados a "Fase 3".
- `pipeline/__init__.py` exporta ahora todas las clases del pipeline.
- CLI acepta `--sources` para filtrar conectores específicos.

### Documentado
- README y AGENTS actualizados para reflejar estado Fase 2→3.
- Este CHANGELOG.md añadido.

## [0.1.0] - 2026-10-22

### Añadido
- **Fase 1**: CLI, modelos Pydantic, SQLite con SQLModel, exportadores Markdown/JSON, progreso por nivel.
- **Fase 2**: Conectores legales OpenAlex, Semantic Scholar, arXiv, Open Library y YouTube con caché SQLite, reintentos, timeouts, rate limiting, normalización a Resource.
- Tests completos, linting con ruff.
