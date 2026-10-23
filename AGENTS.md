# AGENTS.md

## Propósito

RoadmapAI es una CLI local que genera roadmaps de estudio a partir de recursos
académicos legales y verificables. El proyecto se desarrolla por fases.

Estado actual: **Fase 2**, infraestructura de conectores completada. Los
conectores OpenAlex, Semantic Scholar, arXiv, Open Library y YouTube están
implementados con caché SQLite, reintentos, timeouts, rate limiting y
normalización a `Resource`. Falta integrar el pipeline `retrieve`.

## Comandos de desarrollo

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

Para probar la CLI:

```bash
roadmap generate "sistemas de control" --depth 5 --max-resources 20
roadmap list
roadmap show <id>
roadmap export <id> --format markdown
```

## Arquitectura

- `src/roadmap_ai/models.py`: modelos Pydantic del dominio.
- `src/roadmap_ai/storage/`: motor SQLite, tablas SQLModel y repositorios.
- `src/roadmap_ai/sources/`: interfaz común y conectores legales.
- `src/roadmap_ai/pipeline/`: planner, retriever, ranker y builder.
- `src/roadmap_ai/llm/`: contrato del proveedor y prompts.
- `src/roadmap_ai/exporters/`: Markdown y JSON.
- `src/roadmap_ai/cli.py`: comandos Typer.

## Reglas que no se deben romper

- No usar Sci-Hub, Libgen, Z-Library ni sitios de contenido protegido.
- No hacer scraping de ResearchGate.
- Los papers deben venir de APIs legales y públicas.
- El LLM nunca puede inventar recursos, autores, DOI o URLs.
- Todo recurso debe tener una URL HTTP(S) verificable.
- Los tests no deben realizar llamadas reales a internet.
- No registrar claves API ni secretos.
- Mantener código tipado, modular y con docstrings útiles.
- Actualizar los tests al modificar modelos, persistencia o exportadores.
