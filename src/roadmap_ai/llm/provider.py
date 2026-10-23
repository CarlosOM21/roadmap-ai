"""Contrato del proveedor LLM.

La Fase 1 no incluye implementaciones que realicen llamadas de red. Las fases
posteriores añadirán proveedores concretos detrás de este protocolo.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """Error base de la capa LLM."""


class LLMUnavailableError(LLMError):
    """No hay un proveedor configurado o disponible."""


@runtime_checkable
class LLMProvider(Protocol):
    """Interfaz mínima que debe implementar cualquier proveedor LLM."""

    name: str

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
    ) -> str:
        """Devuelve una respuesta textual del modelo."""
        ...


def get_provider(provider_name: str) -> LLMProvider:
    """Devuelve un proveedor configurado.

    Se implementará en la fase de integración del LLM.
    """
    raise LLMUnavailableError(f"El proveedor LLM '{provider_name}' todavía no está implementado")


__all__ = [
    "LLMError",
    "LLMProvider",
    "LLMUnavailableError",
    "get_provider",
]
