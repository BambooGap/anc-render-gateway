from __future__ import annotations

from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.storage.database import get_session
from anc_gateway.storage.repositories import list_recent_patch_records

client = TestClient(app)


def _seed_case_with_patch() -> dict[str, object]:
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_patches_001", "shot_id": "shot_patches_001", "objects": []},
            "render_contract": {"shot_id": "shot_patches_001"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()

    case_response = client.post(
        "/cases",
        json={
            "title": "patches-test-case",
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

    client.post(
        f"/attempts/{attempt['attempt_id']}/manual-job",
        json={"manual_job_id": manual_job["manual_job_id"]},
    )

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

    client.post(
        f"/attempts/{attempt['attempt_id']}/manual-audit",
        json={
            "manual_audit_id": audit["audit_id"],
            "failure_record_id": audit["failure_record_id"],
        },
    )

    patch_response = client.post(f"/failures/{audit['failure_record_id']}/recover")
    assert patch_response.status_code == 200
    patch = patch_response.json()

    return {"case": case, "attempt": attempt, "audit": audit, "patch": patch}


def test_list_recent_patch_records_empty() -> None:
    with get_session() as session:
        patches = list_recent_patch_records(session, limit=10)
    assert patches == []


def test_list_recent_patch_records_returns_data() -> None:
    _seed_case_with_patch()
    with get_session() as session:
        patches = list_recent_patch_records(session, limit=10)
    assert len(patches) >= 1
    assert patches[0].recovery_policy == "LEVEL_2_NEGATIVE_MITIGATION"


def test_casebase_patches_api_endpoint() -> None:
    _seed_case_with_patch()
    response = client.get("/casebase/patches?limit=10")
    assert response.status_code == 200
    patches = response.json()
    assert isinstance(patches, list)
    assert len(patches) >= 1
    assert patches[0]["recovery_policy"] == "LEVEL_2_NEGATIVE_MITIGATION"
    assert patches[0]["patch_prompt"] is not None
