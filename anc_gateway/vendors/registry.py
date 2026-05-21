from __future__ import annotations

from anc_gateway.vendors.base import RenderVendorAdapter
from anc_gateway.vendors.mock_adapter import MockVendorAdapter


class VendorAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, RenderVendorAdapter] = {}

    def register(self, vendor: str, adapter: RenderVendorAdapter) -> None:
        self._adapters[vendor] = adapter

    def get(self, vendor: str) -> RenderVendorAdapter:
        try:
            return self._adapters[vendor]
        except KeyError as exc:
            raise ValueError(f"Unknown render vendor: {vendor}") from exc

    def has(self, vendor: str) -> bool:
        return vendor in self._adapters

    def list_vendors(self) -> list[str]:
        return sorted(self._adapters)


def create_default_registry() -> VendorAdapterRegistry:
    registry = VendorAdapterRegistry()
    registry.register("mock", MockVendorAdapter())
    return registry


default_vendor_registry = create_default_registry()
