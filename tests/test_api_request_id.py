from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def test_request_id_header_is_preserved_when_provided() -> None:
    response = client.get("/health", headers={"X-Request-ID": "req-test-001"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-001"


def test_request_id_header_is_generated_when_missing() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
