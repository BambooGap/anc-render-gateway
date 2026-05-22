from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.attempts.prompt_merge import merge_prompt_with_patch


client = TestClient(app)


def _compile_packet() -> dict[str, object]:
    response = client.post(
        "/compile",
        json={
            "state": {"id": "state_attempt_api", "shot_id": "shot_attempt_api", "objects": []},
            "render_contract": {"shot_id": "shot_attempt_api"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_prompt_merge_appends_patch_prompt_once() -> None:
    base = "她右手握住窗扇右侧金属边框。"
    patch = {"patch_prompt": "窗扇保持垂直平面姿态，只沿上下轨道水平滑动。"}

    merged = merge_prompt_with_patch(base, patch)
    merged_again = merge_prompt_with_patch(merged, patch)

    assert "下一轮修复约束" in merged
    assert "上下轨道水平滑动" in merged
    assert merged_again == merged


def test_case_attempt_lifecycle_api() -> None:
    packet = _compile_packet()
    case_response = client.post(
        "/cases",
        json={
            "title": "Sliding window case",
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
            "platform": "generic_web",
        },
    )
    assert case_response.status_code == 200
    case = case_response.json()

    attempt_response = client.post(
        f"/cases/{case['case_id']}/attempts",
        json={
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
            "compiled_prompt": packet["compiled_prompt"],
            "condition_hash": packet["condition_hash"],
            "source_map": packet["source_map"],
        },
    )
    assert attempt_response.status_code == 200
    attempt = attempt_response.json()
    assert attempt["attempt_index"] == 1
    assert attempt["status"] == "COMPILED"

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
    manual_job = manual_job_response.json()
    link_job_response = client.post(
        f"/attempts/{attempt['attempt_id']}/manual-job",
        json={"manual_job_id": manual_job["manual_job_id"]},
    )
    assert link_job_response.status_code == 200
    assert link_job_response.json()["status"] == "MANUAL_JOB_CREATED"

    audit_response = client.post(
        "/manual-audits",
        json={
            "manual_job_id": manual_job["manual_job_id"],
            "bad_prompt_fragment_ref": "frag_001",
            "failure_type": "window_flipping_bug",
        },
    )
    assert audit_response.status_code == 200
    audit = audit_response.json()
    link_audit_response = client.post(
        f"/attempts/{attempt['attempt_id']}/manual-audit",
        json={
            "manual_audit_id": audit["audit_id"],
            "failure_record_id": audit["failure_record_id"],
        },
    )
    assert link_audit_response.status_code == 200
    assert link_audit_response.json()["status"] == "AUDITED"

    patch_response = client.post(f"/failures/{audit['failure_record_id']}/recover")
    assert patch_response.status_code == 200
    patch = patch_response.json()
    link_patch_response = client.post(
        f"/attempts/{attempt['attempt_id']}/patch",
        json={"patch_packet": patch},
    )
    assert link_patch_response.status_code == 200
    assert link_patch_response.json()["status"] == "PATCHED"

    next_attempt_response = client.post(
        f"/cases/{case['case_id']}/attempts",
        json={
            "previous_attempt_id": attempt["attempt_id"],
            "patch_packet": patch,
        },
    )
    assert next_attempt_response.status_code == 200
    next_attempt = next_attempt_response.json()
    assert next_attempt["attempt_index"] == 2
    assert next_attempt["status"] == "DRAFT"
    assert "下一轮修复约束" in next_attempt["raw_prompt"]

    attempts_response = client.get(f"/cases/{case['case_id']}/attempts")
    assert attempts_response.status_code == 200
    assert len(attempts_response.json()) == 2
