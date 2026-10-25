"""Planificación curricular preliminar (Fase 3)."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from roadmap_ai.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class PlannedLevel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    number: int = Field(ge=1)
    title: str = Field(min_length=1)
    objective: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)


class PlannedRoadmap(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: str = Field(min_length=1)
    levels: list[PlannedLevel] = Field(min_length=4, max_length=10)


@runtime_checkable
class Planner(Protocol):
    async def plan(self, topic: str, depth: int) -> PlannedRoadmap: ...


class HeuristicPlanner:
    def _detect_domain(self, topic: str) -> str:
        t = topic.lower()
        if any(
            k in t
            for k in [
                "mecatr",
                "mecanica",
                "mecánico",
                "diseño mecánico",
                "polea",
                "engran",
                "eje",
                "resistencia",
                "elementos de maquina",
            ]
        ):
            return "mecatronica"
        if any(
            k in t for k in ["control", "sistema de control", "automatico", "pid", "realimentacion"]
        ):
            return "control"
        if any(
            k in t
            for k in [
                "fisica de particulas",
                "mecanica cuantica",
                "electromagnet",
                "termodinam",
                "optica",
            ]
        ):
            return "fisica"
        if any(
            k in t
            for k in [
                "inteligencia artificial",
                "machine learning",
                "deep learning",
                "agente",
                "rl",
                "rag",
                "llm",
            ]
        ):
            return "ia"
        if any(k in t for k in ["matemat", "algebra", "calculo", "estadistica"]):
            return "matematicas"
        if any(k in t for k in ["quimica", "químic"]):
            return "quimica"
        if any(k in t for k in ["biolog", "genet", "bioquim"]):
            return "biologia"
        if any(
            k in t
            for k in ["programacion", "algoritmo", "estructura de datos", "python", "java", "c++"]
        ):
            return "programacion"
        if any(k in t for k in ["economia", "finanz", "contabil"]):
            return "economia"
        if any(k in t for k in ["derecho", "historia", "filosofia", "literatura", "lingüist"]):
            return "humanidades"
        if any(k in t for k in ["electronica", "circuito", "sensores", "microcontrolador"]):
            return "electronica"
        return "generico"

    async def plan(self, topic: str, depth: int) -> PlannedRoadmap:
        depth = max(6, min(10, depth))
        topic_clean = topic.strip()
        domain = self._detect_domain(topic_clean)
        levels_data = []

        if domain == "mecatronica":
            levels_data = [
                PlannedLevel(
                    number=1,
                    title=f"Fundamentos mecánicos y matemáticos para {topic_clean}",
                    objective="Conceptos de estática, cinemática y resistencia",
                    prerequisites=[],
                    concepts=["Estática", "Cinemática", "Resistencia", "Geometría", "Unidades"],
                    projects=[f"Glosario y ejercicios básicos de {topic_clean}"],
                    queries=[
                        f"introduccion {topic_clean}",
                        f"fundamentos mecanica {topic_clean}",
                        f"{topic_clean} libro basico",
                        f"{topic_clean} curso basico",
                        f"{topic_clean} ejercicios",
                        f"{topic_clean} tutorial youtube",
                    ],
                ),
                PlannedLevel(
                    number=2,
                    title=f"Dibujo técnico, CAD y elementos de máquinas para {topic_clean}",
                    objective="Normalización, CAD, ejes, rodamientos, uniones",
                    prerequisites=[f"Fundamentos mecánicos y matemáticos para {topic_clean}"],
                    concepts=["Dibujo técnico", "CAD", "Ejes", "Rodamientos", "Uniones"],
                    projects=[f"Modelado CAD básico para {topic_clean}"],
                    queries=[
                        f"{topic_clean} dibujo tecnico",
                        f"{topic_clean} cad tutorial",
                        f"{topic_clean} ejes poleas",
                        f"{topic_clean} engranajes",
                        f"{topic_clean} elementos maquina",
                        f"{topic_clean} solidworks tutorial youtube",
                    ],
                ),
                PlannedLevel(
                    number=3,
                    title=f"Transmisión, mecanismos y diseño mecánico para {topic_clean}",
                    objective="Poleas, correas, engranajes, reductores, dimensionamiento",
                    prerequisites=[
                        f"Dibujo técnico, CAD y elementos de máquinas para {topic_clean}"
                    ],
                    concepts=[
                        "Transmisión",
                        "Mecanismos",
                        "Engranajes",
                        "Poleas",
                        "Dimensionamiento",
                    ],
                    projects=[f"Diseño de transmisión para {topic_clean}"],
                    queries=[
                        f"{topic_clean} transmision poleas",
                        f"{topic_clean} engranajes diseño",
                        f"{topic_clean} mecanismos",
                        f"{topic_clean} dimensionamiento",
                        f"{topic_clean} ejercicios resueltos",
                        f"{topic_clean} tutorial practico",
                    ],
                ),
                PlannedLevel(
                    number=4,
                    title=f"Electrónica, sensores y actuadores para {topic_clean}",
                    objective="Sensores, actuadores, electrónica básica aplicada",
                    prerequisites=[f"Transmisión, mecanismos y diseño mecánico para {topic_clean}"],
                    concepts=["Sensores", "Actuadores", "Electrónica", "Neumática/Hidráulica"],
                    projects=[f"Selección de sensores/actuadores para {topic_clean}"],
                    queries=[
                        f"{topic_clean} sensores",
                        f"{topic_clean} actuadores",
                        f"{topic_clean} electronica aplicada",
                        f"{topic_clean} arduino tutorial",
                        f"{topic_clean} automatismos",
                        f"{topic_clean} practicas electronica",
                    ],
                ),
                PlannedLevel(
                    number=5,
                    title=f"Sistemas de control y automatización para {topic_clean}",
                    objective="Modelado, PID, lazos de control aplicados",
                    prerequisites=[f"Electrónica, sensores y actuadores para {topic_clean}"],
                    concepts=["Modelado", "PID", "Control", "Automatización"],
                    projects=[f"Control básico aplicado a {topic_clean}"],
                    queries=[
                        f"{topic_clean} control pid",
                        f"{topic_clean} automatizacion",
                        f"{topic_clean} plc tutorial",
                        f"{topic_clean} control sistemas",
                        f"{topic_clean} ejercicios control",
                        f"{topic_clean} laboratorio",
                    ],
                ),
                PlannedLevel(
                    number=6,
                    title=f"Integración mecatrónica, análisis y validación para {topic_clean}",
                    objective="Integración multidisciplinar, análisis, verificación",
                    prerequisites=[f"Sistemas de control y automatización para {topic_clean}"],
                    concepts=["Integración", "Análisis", "Validación", "Prototipado"],
                    projects=[f"Prototipo integrador de {topic_clean}"],
                    queries=[
                        f"{topic_clean} proyecto integrador",
                        f"{topic_clean} prototipo",
                        f"{topic_clean} integracion mecatronica",
                        f"{topic_clean} github proyecto",
                        f"{topic_clean} casos practicos",
                        f"{topic_clean} tutoriales avanzados",
                    ],
                ),
            ]
        elif domain == "control":
            levels_data = [
                PlannedLevel(
                    number=1,
                    title=f"Fundamentos matemáticos para {topic_clean}",
                    objective="Álgebra, cálculo, EDOs básicas",
                    prerequisites=[],
                    concepts=["Cálculo", "EDOs", "Álgebra lineal"],
                    projects=[f"Repaso matemático para {topic_clean}"],
                    queries=[
                        f"{topic_clean} matematicas",
                        f"{topic_clean} ecuaciones diferenciales",
                        f"{topic_clean} algebra lineal",
                        f"{topic_clean} curso basico",
                        f"{topic_clean} ejercicios",
                        f"{topic_clean} tutorial",
                    ],
                ),
                PlannedLevel(
                    number=2,
                    title=f"Modelado de sistemas dinámicos para {topic_clean}",
                    objective="Modelado físico, función de transferencia",
                    prerequisites=[f"Fundamentos matemáticos para {topic_clean}"],
                    concepts=["Modelado", "Función de transferencia", "Diagramas"],
                    projects=[f"Modelado de sistema para {topic_clean}"],
                    queries=[
                        f"{topic_clean} modelado sistemas",
                        f"{topic_clean} funcion transferencia",
                        f"{topic_clean} sistemas dinamicos",
                        f"{topic_clean} ejercicios resueltos",
                        f"{topic_clean} libro",
                        f"{topic_clean} tutorial",
                    ],
                ),
                PlannedLevel(
                    number=3,
                    title=f"Respuesta temporal y estabilidad para {topic_clean}",
                    objective="Respuesta, polos/ceros, estabilidad",
                    prerequisites=[f"Modelado de sistemas dinámicos para {topic_clean}"],
                    concepts=["Respuesta temporal", "Estabilidad", "Polos"],
                    projects=[f"Análisis de estabilidad para {topic_clean}"],
                    queries=[
                        f"{topic_clean} respuesta temporal",
                        f"{topic_clean} estabilidad",
                        f"{topic_clean} polos ceros",
                        f"{topic_clean} ejercicios",
                        f"{topic_clean} practica",
                        f"{topic_clean} simulacion",
                    ],
                ),
                PlannedLevel(
                    number=4,
                    title=f"Control por realimentación y PID para {topic_clean}",
                    objective="Lazo cerrado, PID, sintonización",
                    prerequisites=[f"Respuesta temporal y estabilidad para {topic_clean}"],
                    concepts=["Realimentación", "PID", "Sintonización"],
                    projects=[f"Diseño PID para {topic_clean}"],
                    queries=[
                        f"{topic_clean} pid",
                        f"{topic_clean} control realimentacion",
                        f"{topic_clean} sintonizacion pid",
                        f"{topic_clean} matlab simulink",
                        f"{topic_clean} tutorial practico",
                        f"{topic_clean} laboratorio",
                    ],
                ),
                PlannedLevel(
                    number=5,
                    title=f"Lugar de raíces, frecuencia y diseño avanzado para {topic_clean}",
                    objective="Root locus, bode, diseño avanzado",
                    prerequisites=[f"Control por realimentación y PID para {topic_clean}"],
                    concepts=["Lugar raíces", "Diagrama Bode", "Margenes"],
                    projects=[f"Diseño por frecuencia para {topic_clean}"],
                    queries=[
                        f"{topic_clean} lugar de raices",
                        f"{topic_clean} bode",
                        f"{topic_clean} margen fase ganancia",
                        f"{topic_clean} ejercicios avanzados",
                        f"{topic_clean} simulacion",
                        f"{topic_clean} proyecto",
                    ],
                ),
                PlannedLevel(
                    number=6,
                    title=f"Control moderno, estado y proyectos para {topic_clean}",
                    objective="Espacio de estados, observadores, proyecto integrador",
                    prerequisites=[
                        f"Lugar de raíces, frecuencia y diseño avanzado para {topic_clean}"
                    ],
                    concepts=["Espacio estados", "Observadores", "Controlabilidad"],
                    projects=[f"Proyecto integrador con {topic_clean}"],
                    queries=[
                        f"{topic_clean} espacio de estados",
                        f"{topic_clean} control moderno",
                        f"{topic_clean} observadores",
                        f"{topic_clean} proyecto integrador",
                        f"{topic_clean} github",
                        f"{topic_clean} laboratorio",
                    ],
                ),
            ]
        elif domain == "fisica":
            levels_data = [
                PlannedLevel(
                    number=1,
                    title=f"Fundamentos matemáticos y conceptos para {topic_clean}",
                    objective="Cálculo, vectores, mecánica básica",
                    prerequisites=[],
                    concepts=["Cálculo", "Vectores", "Mecánica"],
                    projects=[f"Glosario de {topic_clean}"],
                    queries=[
                        f"{topic_clean} introduccion",
                        f"{topic_clean} fundamentos",
                        f"{topic_clean} matematicas fisica",
                        f"{topic_clean} curso basico",
                        f"{topic_clean} ejercicios",
                        f"{topic_clean} tutorial",
                    ],
                ),
                PlannedLevel(
                    number=2,
                    title=f"Teoría clásica y experimental para {topic_clean}",
                    objective="Bases teóricas con enfoque experimental",
                    prerequisites=[f"Fundamentos matemáticos y conceptos para {topic_clean}"],
                    concepts=["Teoría", "Experimento", "Mediciones"],
                    projects=[f"Experimento guiado para {topic_clean}"],
                    queries=[
                        f"{topic_clean} teoria",
                        f"{topic_clean} laboratorio",
                        f"{topic_clean} ejercicios resueltos",
                        f"{topic_clean} libro",
                        f"{topic_clean} practicas",
                        f"{topic_clean} problemas",
                    ],
                ),
                PlannedLevel(
                    number=3,
                    title=f"Desarrollo teórico y formalismo para {topic_clean}",
                    objective="Formalismo matemático",
                    prerequisites=[f"Teoría clásica y experimental para {topic_clean}"],
                    concepts=["Formalismo", "Ecuaciones", "Simetrías"],
                    projects=[f"Resolución formal para {topic_clean}"],
                    queries=[
                        f"{topic_clean} formalismo",
                        f"{topic_clean} ecuaciones",
                        f"{topic_clean} libro avanzado",
                        f"{topic_clean} problemas avanzados",
                        f"{topic_clean} ejercicios",
                        f"{topic_clean} tutorial",
                    ],
                ),
                PlannedLevel(
                    number=4,
                    title=f"Aplicaciones, cálculos y modelos para {topic_clean}",
                    objective="Aplicaciones y modelado",
                    prerequisites=[f"Desarrollo teórico y formalismo para {topic_clean}"],
                    concepts=["Aplicaciones", "Modelado", "Cálculos"],
                    projects=[f"Proyecto con cálculos para {topic_clean}"],
                    queries=[
                        f"{topic_clean} aplicaciones",
                        f"{topic_clean} calculos",
                        f"{topic_clean} modelos",
                        f"{topic_clean} ejercicios practicos",
                        f"{topic_clean} simulacion",
                        f"{topic_clean} proyecto",
                    ],
                ),
                PlannedLevel(
                    number=5,
                    title=f"Tópicos avanzados y estado del arte para {topic_clean}",
                    objective="Tópicos especializados",
                    prerequisites=[f"Aplicaciones, cálculos y modelos para {topic_clean}"],
                    concepts=["Tópicos avanzados", "Fenomenología"],
                    projects=[f"Estudio especializado para {topic_clean}"],
                    queries=[
                        f"{topic_clean} avanzado",
                        f"{topic_clean} fenomenologia",
                        f"{topic_clean} papers",
                        f"{topic_clean} review",
                        f"{topic_clean} estado del arte",
                        f"{topic_clean} bibliografia",
                    ],
                ),
                PlannedLevel(
                    number=6,
                    title=f"Investigación, proyecto y síntesis para {topic_clean}",
                    objective="Revisión bibliográfica y proyecto",
                    prerequisites=[f"Tópicos avanzados y estado del arte para {topic_clean}"],
                    concepts=["Investigación", "Síntesis"],
                    projects=[f"Proyecto de investigación para {topic_clean}"],
                    queries=[
                        f"{topic_clean} investigacion",
                        f"{topic_clean} proyecto investigacion",
                        f"{topic_clean} papers cientificos",
                        f"{topic_clean} survey",
                        f"{topic_clean} tesis",
                        f"{topic_clean} recursos completos",
                    ],
                ),
            ]
        elif domain == "ia":
            levels_data = [
                PlannedLevel(
                    number=1,
                    title=f"Fundamentos de {topic_clean}",
                    objective="Conceptos, historia, terminología",
                    prerequisites=[],
                    concepts=["IA", "Agentes", "Problemas"],
                    projects=[f"Mapa conceptual de {topic_clean}"],
                    queries=[
                        f"introduccion {topic_clean}",
                        f"fundamentos {topic_clean}",
                        f"{topic_clean} libro",
                        f"{topic_clean} curso",
                        f"{topic_clean} tutorial youtube",
                        f"{topic_clean} guia",
                    ],
                ),
                PlannedLevel(
                    number=2,
                    title=f"Búsqueda, heurísticas y razonamiento para {topic_clean}",
                    objective="Búsqueda, A*, heurísticas",
                    prerequisites=[f"Fundamentos de {topic_clean}"],
                    concepts=["Búsqueda", "Heurísticas", "Juegos"],
                    projects=[f"Implementar búsqueda para {topic_clean}"],
                    queries=[
                        f"{topic_clean} busqueda heuristica",
                        f"{topic_clean} algoritmos busqueda",
                        f"{topic_clean} ejercicios",
                        f"{topic_clean} tutorial practico",
                        f"{topic_clean} github ejemplos",
                        f"{topic_clean} codigo",
                    ],
                ),
                PlannedLevel(
                    number=3,
                    title=f"Aprendizaje automático para {topic_clean}",
                    objective="Supervisado, validación",
                    prerequisites=[f"Búsqueda, heurísticas y razonamiento para {topic_clean}"],
                    concepts=["ML", "Clasificación", "Validación"],
                    projects=[f"Clasificador para {topic_clean}"],
                    queries=[
                        f"{topic_clean} machine learning",
                        f"{topic_clean} clasificacion",
                        f"{topic_clean} sklearn tutorial",
                        f"{topic_clean} ejercicios practicos",
                        f"{topic_clean} curso",
                        f"{topic_clean} kaggle tutorial",
                    ],
                ),
                PlannedLevel(
                    number=4,
                    title=f"Aprendizaje por refuerzo y MDP para {topic_clean}",
                    objective="MDP, Q-Learning, políticas",
                    prerequisites=[f"Aprendizaje automático para {topic_clean}"],
                    concepts=["MDP", "RL", "Políticas"],
                    projects=[f"Agente RL para {topic_clean}"],
                    queries=[
                        f"{topic_clean} mdp",
                        f"{topic_clean} reinforcement learning",
                        f"{topic_clean} q learning",
                        f"{topic_clean} gymnasium tutorial",
                        f"{topic_clean} practica",
                        f"{topic_clean} github",
                    ],
                ),
                PlannedLevel(
                    number=5,
                    title=f"PLN, RAG y agentes para {topic_clean}",
                    objective="Embeddings, RAG, agentes",
                    prerequisites=[f"Aprendizaje por refuerzo y MDP para {topic_clean}"],
                    concepts=["PLN", "RAG", "Agentes", "Embeddings"],
                    projects=[f"Sistema RAG/agente para {topic_clean}"],
                    queries=[
                        f"{topic_clean} rag",
                        f"{topic_clean} agentes ia",
                        f"{topic_clean} embeddings",
                        f"{topic_clean} langchain tutorial",
                        f"{topic_clean} tutorial practico",
                        f"{topic_clean} github proyecto",
                    ],
                ),
                PlannedLevel(
                    number=6,
                    title=f"Estado del arte, evaluación y proyecto integrador para {topic_clean}",
                    objective="Evaluación, benchmarks, proyecto",
                    prerequisites=[f"PLN, RAG y agentes para {topic_clean}"],
                    concepts=["Evaluación", "Benchmarks", "Proyecto"],
                    projects=[f"Proyecto integrador con {topic_clean}"],
                    queries=[
                        f"{topic_clean} proyecto integrador",
                        f"{topic_clean} papers",
                        f"{topic_clean} estado del arte",
                        f"{topic_clean} evaluacion",
                        f"{topic_clean} github avanzado",
                        f"{topic_clean} recursos completos",
                    ],
                ),
            ]
        else:
            levels_data = [
                PlannedLevel(
                    number=1,
                    title=f"Fundamentos, historia y panorama de {topic_clean}",
                    objective=f"Comprender conceptos y terminología de {topic_clean}",
                    prerequisites=[],
                    concepts=["Conceptos básicos", "Terminología", "Historia"],
                    projects=[f"Mapa conceptual de {topic_clean}"],
                    queries=[
                        f"introduccion {topic_clean}",
                        f"fundamentos {topic_clean}",
                        f"{topic_clean} libro",
                        f"{topic_clean} curso",
                        f"{topic_clean} tutorial youtube",
                        f"{topic_clean} guia",
                    ],
                ),
                PlannedLevel(
                    number=2,
                    title=f"Bases teóricas y herramientas para {topic_clean}",
                    objective="Bases teóricas y herramientas",
                    prerequisites=[f"Fundamentos, historia y panorama de {topic_clean}"],
                    concepts=["Bases teóricas", "Herramientas"],
                    projects=[f"Ejercicios básicos de {topic_clean}"],
                    queries=[
                        f"{topic_clean} fundamentos teoricos",
                        f"{topic_clean} tutorial",
                        f"{topic_clean} ejercicios",
                        f"{topic_clean} documentacion",
                        f"{topic_clean} practicas",
                        f"{topic_clean} ejemplos",
                    ],
                ),
                PlannedLevel(
                    number=3,
                    title=f"Núcleo conceptual y técnicas para {topic_clean}",
                    objective="Conceptos clave y técnicas",
                    prerequisites=[f"Bases teóricas y herramientas para {topic_clean}"],
                    concepts=["Conceptos clave", "Técnicas"],
                    projects=[f"Mini-proyecto de {topic_clean}"],
                    queries=[
                        f"{topic_clean} conceptos clave",
                        f"{topic_clean} tecnicas",
                        f"{topic_clean} libro",
                        f"{topic_clean} ejercicios resueltos",
                        f"{topic_clean} problemas",
                        f"{topic_clean} tutorial practico",
                    ],
                ),
                PlannedLevel(
                    number=4,
                    title=f"Aplicaciones prácticas y proyectos guiados para {topic_clean}",
                    objective="Aplicación a problemas reales",
                    prerequisites=[f"Núcleo conceptual y técnicas para {topic_clean}"],
                    concepts=["Aplicaciones", "Casos de uso"],
                    projects=[f"Proyecto guiado de {topic_clean}"],
                    queries=[
                        f"{topic_clean} aplicaciones",
                        f"{topic_clean} casos de uso",
                        f"{topic_clean} proyecto practico",
                        f"{topic_clean} github ejemplos",
                        f"{topic_clean} tutorial practico",
                        f"{topic_clean} laboratorio",
                    ],
                ),
                PlannedLevel(
                    number=5,
                    title=f"Diseño, análisis y resolución de problemas para {topic_clean}",
                    objective="Diseño, análisis, resolución",
                    prerequisites=[
                        f"Aplicaciones prácticas y proyectos guiados para {topic_clean}"
                    ],
                    concepts=["Diseño", "Análisis"],
                    projects=[f"Proyecto con análisis de {topic_clean}"],
                    queries=[
                        f"{topic_clean} diseño",
                        f"{topic_clean} analisis",
                        f"{topic_clean} ejercicios avanzados",
                        f"{topic_clean} problemas resueltos",
                        f"{topic_clean} tutoriales avanzados",
                        f"{topic_clean} simulacion",
                    ],
                ),
                PlannedLevel(
                    number=6,
                    title=f"Integración, especialización y proyecto final para {topic_clean}",
                    objective="Integración y proyecto final",
                    prerequisites=[
                        f"Diseño, análisis y resolución de problemas para {topic_clean}"
                    ],
                    concepts=["Integración", "Especialización"],
                    projects=[f"Proyecto integrador completo de {topic_clean}"],
                    queries=[
                        f"{topic_clean} proyecto integrador",
                        f"{topic_clean} proyecto completo",
                        f"{topic_clean} github proyecto",
                        f"{topic_clean} papers",
                        f"{topic_clean} estado del arte",
                        f"{topic_clean} recursos completos",
                    ],
                ),
            ]

        if depth > len(levels_data):
            for i in range(len(levels_data), depth):
                n = i + 1
                levels_data.append(
                    PlannedLevel(
                        number=n,
                        title=f"Ampliación y especialización nivel {n} en {topic_clean}",
                        objective="Profundización y proyecto especializado",
                        prerequisites=[levels_data[-1].title],
                        concepts=["Especialización", "Profundización"],
                        projects=[f"Proyecto especializado nivel {n} de {topic_clean}"],
                        queries=[
                            f"{topic_clean} avanzado nivel {n}",
                            f"{topic_clean} tutorial avanzado",
                            f"{topic_clean} ejercicios avanzados",
                            f"{topic_clean} github avanzado",
                            f"{topic_clean} papers",
                            f"{topic_clean} casos reales",
                        ],
                    )
                )
        return PlannedRoadmap(topic=topic_clean, levels=levels_data[:depth])


class LLMPlanner:
    def __init__(self, provider: LLMProvider | None = None, use_llm: bool = False) -> None:
        self.provider = provider
        self.use_llm = use_llm
        self._heuristic = HeuristicPlanner()

    async def plan(self, topic: str, depth: int) -> PlannedRoadmap:
        if self.use_llm and self.provider is not None:
            try:
                logger.info("LLM planner solicitado pero usando heurístico por seguridad")
            except Exception as exc:
                logger.warning("LLM planner falló, usando heurístico: %s", exc)
        return await self._heuristic.plan(topic, depth)


__all__ = ["HeuristicPlanner", "LLMPlanner", "PlannedLevel", "PlannedRoadmap", "Planner"]
