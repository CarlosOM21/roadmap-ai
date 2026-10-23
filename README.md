# RoadmapAI

CLI local para generar roadmaps de estudio académicos a partir de recursos
reales, legales y verificables. El proyecto está diseñado para funcionar por
fases y, en su versión final, combinará recuperación de fuentes con un LLM que
solo organiza y redacta los recursos encontrados.

> **Estado actual: Fase 2 (infraestructura completada).** La CLI, los modelos,
> SQLite, los exportadores y los tests están operativos. Se han añadido los
> conectores legales OpenAlex, Semantic Scholar, arXiv, Open Library y YouTube
> con caché SQLite, reintentos, timeouts, rate limiting y normalización a
> `Resource`. La integración con el pipeline queda pendiente.

## Características de la Fase 1

- Proyecto instalable con `pyproject.toml` y paquete en `src/`.
- Modelos Pydantic para temas, recursos, niveles, roadmaps y resultados de fuentes.
- Persistencia SQLite con SQLModel y repositorios.
- Tablas para `topics`, `roadmaps`, `resources`, `roadmap_levels`,
  `roadmap_resources` y `user_progress`.
- CLI con Typer y salida enriquecida con Rich.
- Exportación a Markdown y JSON.
- Progreso por nivel persistido.
- Datos de ejemplo con enlaces reales y claramente identificados como demo.
- Tests aislados, sin llamadas a internet.

## Requisitos

- Python 3.11 o superior.
- Un entorno virtual recomendado.

## Instalación

```bash
cd /home/carlos/Documentos/proyectos/roadmap-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

Edita `.env` y añade las claves que vayas a utilizar en fases posteriores. La
Fase 1 funciona sin ninguna clave.

## Configuración

Las variables disponibles se documentan en `.env.example`:

| Variable | Valor por defecto | Uso |
| --- | --- | --- |
| `LLM_PROVIDER` | `openai` | Proveedor previsto para el LLM |
| `LLM_API_KEY` | vacío | Clave del proveedor |
| `LLM_MODEL` | `gpt-4o-mini` | Modelo previsto |
| `OPENALEX_EMAIL` | vacío | Email para el User-Agent de OpenAlex |
| `SEMANTIC_SCHOLAR_API_KEY` | vacío | Clave opcional de Semantic Scholar |
| `YOUTUBE_API_KEY` | vacío | Clave de YouTube Data API v3 |
| `DATABASE_URL` | `sqlite:///data/roadmaps.db` | Base de datos SQLite |
| `REQUEST_TIMEOUT` | `20` | Timeout HTTP en segundos |
| `MAX_RETRIES` | `3` | Reintentos HTTP |
| `LOG_LEVEL` | `INFO` | Nivel de logging |

La base de datos se crea automáticamente en la primera ejecución. La ruta relativa
se interpreta desde el directorio donde ejecutes la CLI.

## Uso

### Generar un roadmap de demostración

```bash
roadmap generate "sistemas de control" --depth 5 --max-resources 20
```

Opciones principales:

- `--depth`: número de niveles, entre 4 y 6.
- `--max-resources`: límite de recursos incluidos.
- `--output`: exporta además a un archivo. Se usa JSON si la extensión es
  `.json`; en caso contrario, Markdown.
- `--no-llm`: se acepta para preparar la interfaz de la Fase 4. En esta fase el
  resultado ya es local y no usa LLM.

Ejemplo con exportación:

```bash
roadmap generate "sistemas de control" --max-resources 20 --output roadmap.md
```

### Listar y consultar roadmaps

```bash
roadmap list
roadmap show <roadmap-id>
```

Los identificadores se pueden abreviar usando un prefijo único.

### Exportar

```bash
roadmap export <roadmap-id> --format markdown
roadmap export <roadmap-id> --format json --output roadmap.json
```

Si no se indica `--output`, se crea un archivo dentro de `exports/`.

### Marcar progreso

```bash
roadmap progress <roadmap-id> --complete "Nivel 1"
roadmap progress <roadmap-id> --complete "Nivel 1" --uncomplete
```

### Actualizar un roadmap

```bash
roadmap update <roadmap-id>
```

En la Fase 1 vuelve a generar los datos de demostración, conserva el
identificador y el progreso existente.

## Estructura del proyecto

```text
roadmap-ai/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── AGENTS.md
├── src/roadmap_ai/
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── sample_data.py
│   ├── llm/
│   ├── sources/
│   ├── pipeline/
│   ├── storage/
│   └── exporters/
├── tests/
└── data/
```

## Tests

```bash
pytest
```

Los tests usan bases de datos temporales y respuestas simuladas. No realizan
peticiones de red.

Para comprobar estilo:

```bash
ruff check .
ruff format --check .
```

## Base de datos

El esquema se crea con SQLModel sobre SQLite. Las operaciones principales están
en `RoadmapRepository`:

- guardar y recuperar roadmaps completos;
- listar resúmenes con progreso;
- marcar o desmarcar niveles completados;
- resolver identificadores por prefijo único.

## Fuentes legales previstas

La Fase 2 incorporará conectores independientes para OpenAlex, Semantic Scholar,
arXiv, Open Library y YouTube Data API. Solo se usarán APIs públicas y metadatos
legales. No se implementará scraping de ResearchGate ni acceso a repositorios de
contenido protegido.

## Próximas fases

1. **Fase 2:** conectores de fuentes con reintentos, timeouts y caché.
2. **Fase 3:** planner, retriever, ranker y builder.
3. **Fase 4:** CLI completa con `--offline`, `--no-llm`, actualización y
   advertencias por fuente.
4. **Fase 5:** exportadores definitivos.
5. **Fase 6:** cobertura completa de pruebas y endurecimiento.
