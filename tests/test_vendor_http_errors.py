import httpx
import pytest

from anc_gateway.storage.models import RenderJobModel
from anc_gateway.vendors.base import VendorCancelResult, VendorRenderStatus, VendorSubmitResult
from anc_gateway.vendors.config import VendorHTTPConfig
from anc_gateway.vendors.errors import VendorHTTPError, VendorResponseParseError
from anc_gateway.vendors.http_base import HTTPVendorAdapterBase


class ErroringHTTPAdapter(HTTPVendorAdapterBase):
    def submit_render_job(self, job: RenderJobModel) -> VendorSubmitResult:
        raise NotImplementedError

    def get_render_status(self, external_job_id: str) -> VendorRenderStatus:
        raise NotImplementedError

    def cancel_render_job(self, external_job_id: str) -> VendorCancelResult:
        raise NotImplementedError


def _adapter_for_response(response: httpx.Response) -> ErroringHTTPAdapter:
    def handler(request: httpx.Request) -> httpx.Response:
        return response

    return ErroringHTTPAdapter(
        VendorHTTPConfig(
            vendor="erroring",
            model="erroring-model",
            base_url="https://erroring.vendor.local",
            api_key_env="ERRORING_VENDOR_API_KEY",
        ),
        transport=httpx.MockTransport(handler),
    )


def test_http_error_does_not_leak_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ERRORING_VENDOR_API_KEY", "super-secret-key")
    adapter = _adapter_for_response(httpx.Response(500, json={"error": "boom"}))

    with pytest.raises(VendorHTTPError) as exc_info:
        adapter.post_json("/renders", {"prompt": "x"})

    assert "super-secret-key" not in str(exc_info.value)
    assert "HTTP 500" in str(exc_info.value)


def test_non_json_response_raises_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ERRORING_VENDOR_API_KEY", "super-secret-key")
    adapter = _adapter_for_response(httpx.Response(200, content=b"not-json"))

    with pytest.raises(VendorResponseParseError):
        adapter.get_json("/renders/1")
