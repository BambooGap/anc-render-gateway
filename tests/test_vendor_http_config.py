import pytest

from anc_gateway.vendors.config import VendorHTTPConfig, load_api_key
from anc_gateway.vendors.errors import VendorConfigurationError


def test_load_api_key_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_VENDOR_API_KEY", "secret-value")

    assert load_api_key("TEST_VENDOR_API_KEY") == "secret-value"


def test_load_api_key_missing_raises_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MISSING_VENDOR_API_KEY", raising=False)

    with pytest.raises(VendorConfigurationError) as exc_info:
        load_api_key("MISSING_VENDOR_API_KEY")

    assert "MISSING_VENDOR_API_KEY" in str(exc_info.value)


def test_vendor_http_config_defaults() -> None:
    config = VendorHTTPConfig(
        vendor="fake-http",
        model="fake-http-video-v1",
        base_url="https://fake-http.vendor.local",
        api_key_env="FAKE_HTTP_API_KEY",
    )

    assert config.timeout_seconds == 60.0
    assert config.poll_interval_seconds == 5.0
    assert config.max_poll_attempts == 60
