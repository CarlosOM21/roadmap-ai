"""Cliente HTTP asíncrono con timeouts, reintentos y rate limiting."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from roadmap_ai.sources.errors import SourceHTTPError, SourceNetworkError, SourceParseError

logger = logging.getLogger(__name__)

SleepFunction = Callable[[float], Awaitable[None]]
ClockFunction = Callable[[], float]


class AsyncRateLimiter:
    """Serializa peticiones y respeta un intervalo mínimo entre ellas."""

    def __init__(
        self,
        min_interval: float,
        *,
        sleep: SleepFunction = asyncio.sleep,
        clock: ClockFunction = time.monotonic,
    ) -> None:
        self.min_interval = max(0.0, min_interval)
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        """Espera si es necesario antes de la siguiente petición."""
        async with self._lock:
            if self._last_request is not None:
                elapsed = self._clock() - self._last_request
                delay = self.min_interval - elapsed
                if delay > 0:
                    await self._sleep(delay)
            self._last_request = self._clock()


class HttpClient:
    """Pequeño wrapper de ``httpx`` con política de reintentos uniforme."""

    def __init__(
        self,
        *,
        source: str,
        timeout: float,
        max_retries: int,
        user_agent: str,
        min_interval: float = 0.0,
        client: httpx.AsyncClient | None = None,
        sleep: SleepFunction = asyncio.sleep,
        backoff_base: float = 0.5,
        max_backoff: float = 8.0,
    ) -> None:
        self.source = source
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.user_agent = user_agent
        self.backoff_base = max(0.0, backoff_base)
        self.max_backoff = max(0.0, max_backoff)
        self._sleep = sleep
        self._limiter = AsyncRateLimiter(min_interval, sleep=sleep)
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
        return self._client

    def _retry_delay(self, attempt: int, response: httpx.Response) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(max(float(retry_after), 0.0), self.max_backoff)
            except ValueError:
                pass
        return min(self.backoff_base * (2**attempt), self.max_backoff)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        client = await self._get_client()
        request_headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
        }
        if headers:
            request_headers.update(headers)

        attempts = self.max_retries + 1
        for attempt in range(attempts):
            await self._limiter.wait()
            try:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt >= self.max_retries:
                    raise SourceNetworkError(
                        self.source,
                        f"fallo de red tras {attempts} intentos ({type(exc).__name__})",
                    ) from exc
                delay = min(self.backoff_base * (2**attempt), self.max_backoff)
                logger.warning(
                    "%s: fallo de red (%s); reintento %d/%d en %.1fs",
                    self.source,
                    type(exc).__name__,
                    attempt + 1,
                    self.max_retries,
                    delay,
                )
                await self._sleep(delay)
                continue

            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt >= self.max_retries:
                    raise SourceHTTPError(
                        self.source,
                        response.status_code,
                        f"HTTP {response.status_code} tras {attempts} intentos",
                    )
                delay = self._retry_delay(attempt, response)
                logger.warning(
                    "%s: HTTP %d; reintento %d/%d en %.1fs",
                    self.source,
                    response.status_code,
                    attempt + 1,
                    self.max_retries,
                    delay,
                )
                await self._sleep(delay)
                continue

            if response.status_code >= 400:
                raise SourceHTTPError(
                    self.source,
                    response.status_code,
                    f"HTTP {response.status_code}",
                )
            return response

        raise SourceNetworkError(self.source, "se agotaron los reintentos")

    async def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Obtiene y decodifica una respuesta JSON."""
        response = await self._request("GET", url, params=params, headers=headers)
        try:
            return response.json()
        except ValueError as exc:
            raise SourceParseError(self.source, "respuesta JSON inválida") from exc

    async def get_text(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        """Obtiene una respuesta textual, por ejemplo XML de arXiv."""
        response = await self._request("GET", url, params=params, headers=headers)
        return response.text

    async def aclose(self) -> None:
        """Cierra el cliente solo si fue creado internamente."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None


__all__ = ["AsyncRateLimiter", "HttpClient", "SleepFunction"]
