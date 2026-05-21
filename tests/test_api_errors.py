from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def _compiled_packet() -> dict[str, object]:
    response = client.post(
        "/compile",
        json={
            "state": {"id": "state_error", "shot_id": "shot_error", "objects": []},
            "render_contract": {"shot_id": "shot_error"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_source_map_attribution_error_uses_structured_error_format() -> None:
    response = client.post(
        "/audit",
        headers={"X-Request-ID": "req-error-001"},
        json={
            "audit": {
                "ok": False,
                "raw_signature": "window_flipping_bug",
                "bad_prompt_fragment_ref": "frag_999",
            },
            "packet": _compiled_packet(),
        },
    )

    assert response.status_code == 400
    assert response.headers["X-Request-ID"] == "req-error-001"
    payload = response.json()
    assert payload["error"]["code"] == "SOURCE_MAP_ATTRIBUTION_ERROR"
    assert payload["error"]["request_id"] == "req-error-001"
    assert "frag_999" in payload["error"]["message"]


def test_validation_error_uses_structured_error_format() -> None:
    response = client.post(
        "/compile",
        headers={"X-Request-ID": "req-validation-001"},
        json={
            "state": {"id": "state_validation", "shot_id": "shot_validation"},
            "render_contract": {"shot_id": "shot_validation"},
        },
    )

    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == "req-validation-001"
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["request_id"] == "req-validation-001"
    assert "raw_prompt" in payload["error"]["message"]
