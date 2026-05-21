from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.vendors.capabilities import get_vendor_capability


client = TestClient(app)


def test_mock_capability_supports_text_to_video() -> None:
    capability = get_vendor_capability("mock")

    assert capability.vendor == "mock"
    assert capability.model == "mock-video-v1"
    assert capability.text_to_video is True
    assert capability.image_to_video is True
    assert capability.first_frame is True
    assert capability.inpainting_mask is False
    assert capability.seed is False


def test_vendors_api_returns_mock_and_capability() -> None:
    vendors_response = client.get("/vendors")
    capability_response = client.get("/vendors/mock/capabilities")

    assert vendors_response.status_code == 200
    assert "mock" in vendors_response.json()
    assert capability_response.status_code == 200
    assert capability_response.json()["text_to_video"] is True
