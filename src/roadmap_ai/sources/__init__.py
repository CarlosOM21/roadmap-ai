"""Conectores de fuentes académicas legales."""

from roadmap_ai.sources.arxiv import ArxivSource
from roadmap_ai.sources.base import BaseSource, Source
from roadmap_ai.sources.errors import (
    SourceError,
    SourceHTTPError,
    SourceNetworkError,
    SourceParseError,
    SourceUnavailableError,
)
from roadmap_ai.sources.http import AsyncRateLimiter, HttpClient
from roadmap_ai.sources.open_library import OpenLibrarySource
from roadmap_ai.sources.openalex import OpenAlexSource
from roadmap_ai.sources.semantic_scholar import SemanticScholarSource
from roadmap_ai.sources.youtube import YouTubeSource
from roadmap_ai.sources.github import GitHubSource

__all__ = [
    "ArxivSource",
    "AsyncRateLimiter",
    "BaseSource",
    "HttpClient",
    "OpenAlexSource",
    "OpenLibrarySource",
    "SemanticScholarSource",
    "Source",
    "SourceError",
    "SourceHTTPError",
    "SourceNetworkError",
    "SourceParseError",
    "SourceUnavailableError",
    "YouTubeSource",
    "GitHubSource",
]
