from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def _compiled_packet() -> dict[str, object]:
    response = client.post(
        "/compile",
        json={
            "state": {
                "id": "state_api_audit",
                "shot_id": "shot_api_audit",
                "objects": [],
            },
            "render_contract": {"shot_id": "shot_api_audit"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_audit_endpoint_normalizes_window_flip_and_attributes_fragment() -> None:
    packet = _compiled_packet()
    response = client.post(
        "/audit",
        json={
            "audit": {
                "ok": False,
                "raw_signature": "window_flipping_bug",
                "bad_prompt_fragment_ref": "frag_001",
            },
            "packet": packet,
        },
    )

    assert response.status_code == 200
    record = response.json()
    assert record["signature"] == "object_rotation_error"
    assert record["category"] == "topology_dof_violation"
    assert record["bad_prompt_fragment_ref"] == "frag_001"
    assert record["bad_prompt_fragment"] == "她轻轻推开了推拉窗"


def test_audit_endpoint_returns_null_when_passed_is_true() -> None:
    packet = _compiled_packet()
    response = client.post(
        "/audit",
        json={
            "audit": {
                "passed": True,
                "raw_signature": "window_flipping_bug",
                "bad_prompt_fragment_ref": "frag_001",
            },
            "packet": packet,
        },
    )

    assert response.status_code == 200
    assert response.json() is None
