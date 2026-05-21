from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def test_version_endpoint_returns_service_metadata() -> None:
    response = client.get("/version")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "anc-render-gateway"
    assert payload["phase"] == "5A"
    assert payload["compiler_version"]
    assert payload["ruleset_fingerprint"]
