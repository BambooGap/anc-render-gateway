from __future__ import annotations

from typing import Any

import httpx

from anc_gateway.vendors.base import RenderVendorAdapter
from anc_gateway.vendors.config import VendorHTTPConfig, load_api_key
from anc_gateway.vendors.errors import VendorHTTPError, VendorResponseParseError, VendorTimeoutError


class HTTPVendorAdapterBase(RenderVendorAdapter):
    def __init__(
        self,
        config: VendorHTTPConfig,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config
        self._transport = transport

    def build_headers(self) -> dict[str, str]:
        api_key = load_api_key(self.config.api_key_env)
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            with self._client() as client:
                response = client.post(path, json=payload, headers=self.build_headers())
        except httpx.TimeoutException as exc:
            raise VendorTimeoutError(
                f"Vendor request timed out for {self.config.vendor}: POST {path}"
            ) from exc
        except httpx.HTTPError as exc:
            raise VendorHTTPError(f"Vendor HTTP request failed for {self.config.vendor}") from exc
        return self._parse_json_response(response, method="POST", path=path)

    def get_json(self, path: str) -> dict[str, Any]:
        try:
            with self._client() as client:
                response = client.get(path, headers=self.build_headers())
        except httpx.TimeoutException as exc:
            raise VendorTimeoutError(
                f"Vendor request timed out for {self.config.vendor}: GET {path}"
            ) from exc
        except httpx.HTTPError as exc:
            raise VendorHTTPError(f"Vendor HTTP request failed for {self.config.vendor}") from exc
        return self._parse_json_response(response, method="GET", path=path)

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
            transport=self._transport,
        )

    def _parse_json_response(
        self,
        response: httpx.Response,
        method: str,
        path: str,
    ) -> dict[str, Any]:
        if response.status_code >= 400:
            raise VendorHTTPError(
                f"Vendor {self.config.vendor} returned HTTP {response.status_code} for {method} {path}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise VendorResponseParseError(
                f"Vendor {self.config.vendor} returned a non-JSON response for {method} {path}"
            ) from exc
        if not isinstance(payload, dict):
            raise VendorResponseParseError(
                f"Vendor {self.config.vendor} returned a non-object JSON response for {method} {path}"
            )
        return payload
