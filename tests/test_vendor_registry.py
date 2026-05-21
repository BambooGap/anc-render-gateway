from anc_gateway.vendors.registry import default_vendor_registry


def test_default_registry_has_mock_vendor() -> None:
    assert default_vendor_registry.has("mock")
    assert "mock" in default_vendor_registry.list_vendors()
