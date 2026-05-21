from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def _create_failure_record() -> str:
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_failure_recover", "shot_id": "shot_failure_recover", "objects": []},
            "render_contract": {"shot_id": "shot_failure_recover"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()
    manual_job_response = client.post(
        "/manual-jobs",
        json={
            "condition_hash": packet["condition_hash"],
            "compiled_prompt": packet["compiled_prompt"],
            "source_map": packet["source_map"],
            "platform": "generic_web",
        },
    )
    assert manual_job_response.status_code == 200
    audit_response = client.post(
        "/manual-audits",
        json={
            "manual_job_id": manual_job_response.json()["manual_job_id"],
            "bad_prompt_fragment_ref": "frag_001",
            "failure_type": "window_flipping_bug",
        },
    )
    assert audit_response.status_code == 200
    return str(audit_response.json()["failure_record_id"])


def test_recover_failure_record_by_id_returns_patch_packet() -> None:
    failure_record_id = _create_failure_record()

    response = client.post(f"/failures/{failure_record_id}/recover")

    assert response.status_code == 200
    payload = response.json()
    assert payload["recovery_policy"] == "LEVEL_2_NEGATIVE_MITIGATION"
    assert "窗扇保持垂直平面姿态" in payload["patch_prompt"]


def test_recover_missing_failure_record_returns_structured_error() -> None:
    response = client.post(
        "/failures/missing-failure-id/recover",
        headers={"X-Request-ID": "req-missing-failure"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "VALUE_ERROR"
    assert payload["error"]["request_id"] == "req-missing-failure"
