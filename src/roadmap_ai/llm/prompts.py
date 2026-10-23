"""Prompts del sistema y plantillas para el pipeline con LLM."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "Eres un diseñador de currículos académicos. Tu tarea es crear roadmaps de "
    "estudio claros, progresivos y prácticos para estudiantes universitarios.\n\n"
    "Reglas:\n"
    "- Usa exclusivamente los recursos proporcionados en el contexto.\n"
    "- No inventes títulos, autores, enlaces, DOIs, cursos ni papers.\n"
    "- Si un recurso no es relevante, descártalo.\n"
    "- Organiza los recursos por nivel de dificultad.\n"
    "- Prioriza recursos abiertos, completos, recientes y de fuentes confiables.\n"
    "- Para cada nivel incluye: objetivo, conceptos, recursos y proyecto práctico.\n"
    "- Si no hay suficientes recursos para un nivel, indícalo explícitamente como "
    '"recursos insuficientes".\n'
    "- Responde exclusivamente en JSON válido conforme al esquema proporcionado.\n"
    "- Escribe en español neutro."
)

PLANNER_SCHEMA = """{
  "topic": "string",
  "levels": [
    {
      "number": 1,
      "title": "string",
      "objective": "string",
      "prerequisites": ["string"],
      "concepts": ["string"],
      "projects": ["string"],
      "queries": ["string"]
    }
  ]
}"""

BUILDER_SCHEMA = """{
  "topic": "string",
  "title": "string",
  "description": "string",
  "levels": [
    {
      "number": 1,
      "title": "string",
      "objective": "string",
      "prerequisites": ["string"],
      "concepts": ["string"],
      "projects": ["string"],
      "resources": [
        {
          "resource_id": "string",
          "rationale": "string"
        }
      ]
    }
  ]
}"""


def render_planner_prompt(topic: str, depth: int) -> str:
    """Construye la petición de planificación curricular."""
    return (
        f"Crea la estructura preliminar de un roadmap sobre: {topic!r}.\n"
        f"Genera exactamente {depth} niveles progresivos, con objetivos, "
        "prerrequisitos, conceptos clave, proyectos prácticos y entre 2 y 4 "
        "queries de búsqueda por nivel. No incluyas recursos concretos todavía.\n\n"
        f"Esquema JSON requerido:\n{PLANNER_SCHEMA}"
    )


def render_builder_prompt(
    topic: str,
    planned_roadmap_json: str,
    resources_json: str,
) -> str:
    """Construye la petición para asignar y explicar recursos ya recuperados."""
    return (
        f"Tema: {topic!r}\n\n"
        "Estructura preliminar:\n"
        f"{planned_roadmap_json}\n\n"
        "Recursos recuperados y verificados (única fuente permitida):\n"
        f"{resources_json}\n\n"
        "Asigna únicamente recursos presentes en el contexto. Usa sus "
        "`resource_id` y explica brevemente por qué cada uno es útil. No añadas "
        "autores, URLs, DOIs ni títulos que no aparezcan en los datos.\n\n"
        f"Esquema JSON requerido:\n{BUILDER_SCHEMA}"
    )


__all__ = [
    "BUILDER_SCHEMA",
    "PLANNER_SCHEMA",
    "SYSTEM_PROMPT",
    "render_builder_prompt",
    "render_planner_prompt",
]
