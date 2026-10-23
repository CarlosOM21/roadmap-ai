"""Utilidades de normalización compartidas por los conectores."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import urlparse

from roadmap_ai.models import slugify


def normalize_whitespace(value: str | None) -> str:
    """Compacta espacios y saltos de línea."""
    if not value:
        return ""
    return " ".join(value.split())


def truncate(value: str | None, max_chars: int = 1500) -> str:
    """Recorta texto preservando palabras completas cuando es posible."""
    normalized = normalize_whitespace(value)
    if len(normalized) <= max_chars:
        return normalized
    cut = normalized[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return f"{cut}..."


def safe_http_url(value: object) -> str | None:
    """Devuelve una URL HTTP(S) válida o ``None``."""
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return candidate


def doi_url(doi: str) -> str:
    """Construye la URL canónica de un DOI."""
    return f"https://doi.org/{doi.strip()}"


def stable_resource_id(source: str, identifier: str) -> str:
    """Genera un id determinista para un recurso de una fuente."""
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:20]
    return f"{slugify(source)}-{digest}"


def year_from_iso(value: object) -> int | None:
    """Extrae el año de una fecha ISO o de un entero plausible."""
    if isinstance(value, int) and 1000 <= value <= 2200:
        return value
    if not isinstance(value, str) or not value.strip():
        return None

    raw = value.strip()
    try:
        year = datetime.fromisoformat(raw.replace("Z", "+00:00")).year
    except ValueError:
        match = re.search(r"\b(1\d{3}|20\d{2}|21\d{2})\b", raw)
        return int(match.group(1)) if match else None
    return year


__all__ = [
    "doi_url",
    "normalize_whitespace",
    "safe_http_url",
    "stable_resource_id",
    "truncate",
    "year_from_iso",
]
