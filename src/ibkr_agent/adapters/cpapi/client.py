"""Low-level HTTP client for the CPAPI.

The CPAPI runs behind a local gateway with a self-signed certificate, hence
``verify=False``. The ``base_url`` already includes ``/v1/api``; for httpx to
concatenate correctly, we normalize the base_url with a trailing slash and strip
the leading slash from the endpoint (otherwise httpx would drop the ``/v1/api``).
"""

from __future__ import annotations

from typing import Any

import httpx


class CpapiError(Exception):
    """Communication or business error coming from the CPAPI."""

    def __init__(self, message: str, *, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class CpapiClient:
    def __init__(self, base_url: str, *, timeout: float = 15.0):
        normalized = base_url if base_url.endswith("/") else base_url + "/"
        self._client = httpx.AsyncClient(base_url=normalized, verify=False, timeout=timeout)

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict | None = None,
        json: Any | None = None,
    ) -> Any:
        path = endpoint.lstrip("/")
        try:
            response = await self._client.request(method, path, params=params, json=json)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            payload = _safe_json(exc.response)
            raise CpapiError(
                f"CPAPI {method} {path} failed: HTTP {exc.response.status_code}",
                status=exc.response.status_code,
                payload=payload,
            ) from exc
        except httpx.HTTPError as exc:
            raise CpapiError(
                f"Communication failure with the CPAPI at {path}: {exc}. "
                "Is the Client Portal Gateway running and logged in?"
            ) from exc

        if not response.content:
            return None
        return _safe_json(response)

    async def get(self, endpoint: str, *, params: dict | None = None) -> Any:
        return await self.request("GET", endpoint, params=params)

    async def post(self, endpoint: str, *, json: Any | None = None) -> Any:
        return await self.request("POST", endpoint, json=json)

    async def delete(self, endpoint: str) -> Any:
        return await self.request("DELETE", endpoint)

    async def aclose(self) -> None:
        await self._client.aclose()


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text
