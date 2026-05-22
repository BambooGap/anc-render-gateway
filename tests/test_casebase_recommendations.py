from __future__ import annotations

from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.casebase.recommendations import recommend_patches
from anc_gateway.casebase.schemas import RecommendRequest
from anc_gateway.storage.database import get_session

client = TestClient(app)


def _seed_case_with_patch() -> None:
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_rec_001", "shot_id": "shot_rec_001", "objects": []},
            "render_contract": {"shot_id": "shot_rec_001"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()

    case_response = client.post(
        "/cases",
        json={
            "title": "recommend-test-case",
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


def test_recommend_patches_empty_without_data() -> None:
    with get_session() as session:
        request = RecommendRequest(failure_signature="nonexistent_sig", limit=5)
        result = recommend_patches(session, request)
    assert result.recommended_patches == []
    assert result.total_candidates == 0


def test_recommend_patches_exact_signature_match() -> None:
    _seed_case_with_patch()
    with get_session() as session:
        request = RecommendRequest(failure_signature="object_rotation_error", limit=5)
        result = recommend_patches(session, request)
    assert len(result.recommended_patches) >= 1
    assert result.recommended_patches[0].confidence == 0.9
    assert result.recommended_patches[0].matched_by == "exact_signature"
    assert result.recommended_patches[0].failure_signature == "object_rotation_error"


def test_recommend_patches_api_endpoint() -> None:
    _seed_case_with_patch()
    response = client.post(
        "/casebase/recommend-patches",
        json={"failure_signature": "object_rotation_error", "limit": 5},
    )
    assert response.status_code == 200
    result = response.json()
    assert "recommended_patches" in result
    assert len(result["recommended_patches"]) >= 1
    assert result["recommended_patches"][0]["confidence"] == 0.9


def test_recommend_patches_with_text_fragment() -> None:
    _seed_case_with_patch()
    with get_session() as session:
        request = RecommendRequest(
            failure_signature="nonexistent_sig",
            bad_prompt_fragment="推拉窗",
            limit=5,
        )
        result = recommend_patches(session, request)
    assert isinstance(result.recommended_patches, list)
