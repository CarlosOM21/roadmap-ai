"""Errores normalizados de los conectores de fuentes."""

from __future__ import annotations


class SourceError(Exception):
    """Error base de una consulta a una fuente externa."""

    def __init__(self, source: str, message: str) -> None:
        self.source = source
        self.message = message
        super().__init__(f"{source}: {message}")


class SourceHTTPError(SourceError):
    """La fuente respondió con un estado HTTP no recuperable."""

    def __init__(self, source: str, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        detail = message or f"HTTP {status_code}"
        super().__init__(source, detail)


class SourceNetworkError(SourceError):
    """Fallo de red, timeout o conexión tras agotar los reintentos."""


class SourceParseError(SourceError):
    """La respuesta de la fuente no tiene el formato esperado."""


class SourceUnavailableError(SourceError):
    """La fuente no está configurada, por ejemplo por falta de API key."""


__all__ = [
    "SourceError",
    "SourceHTTPError",
    "SourceNetworkError",
    "SourceParseError",
    "SourceUnavailableError",
]
