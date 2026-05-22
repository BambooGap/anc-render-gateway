"""Tests for recommend reason text and matched_by fields."""

from __future__ import annotations

from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.casebase.recommendations import recommend_patches
from anc_gateway.casebase.schemas import RecommendRequest
from anc_gateway.storage.database import get_session

client = TestClient(app)


def _seed_reason_case() -> None:
    compile_resp = client.post(
        "/compile",
        json={
            "state": {"id": "state_reason_001", "shot_id": "shot_reason_001", "objects": []},
            "render_contract": {"shot_id": "shot_reason_001"},
            "raw_prompt": "阀门在旋转时发生角度翻转。",
        },
    )
    assert compile_resp.status_code == 200
    packet = compile_resp.json()

    case_resp = client.post(
        "/cases",
        json={"title": "reason-test-case", "raw_prompt": "阀门在旋转时发生角度翻转。", "platform": "generic_web"},
    )
    assert case_resp.status_code == 200
    case = case_resp.json()

    attempt_resp = client.post(
        f"/cases/{case['case_id']}/attempts",
        json={
            "raw_prompt": "阀门在旋转时发生角度翻转。",
            "compiled_prompt": packet["compiled_prompt"],
            "condition_hash": packet["condition_hash"],
            "source_map": packet["source_map"],
        },
    )
    assert attempt_resp.status_code == 200
    attempt = attempt_resp.json()

    job_resp = client.post(
        "/manual-jobs",
        json={
            "condition_hash": packet["condition_hash"],
            "compiled_prompt": packet["compiled_prompt"],
            "source_map": packet["source_map"],
            "platform": "generic_web",
        },
    )
    assert job_resp.status_code == 200
    manual_job = job_resp.json()

    client.post(
        f"/attempts/{attempt['attempt_id']}/manual-job",
        json={"manual_job_id": manual_job["manual_job_id"]},
    )

    audit_resp = client.post(
        "/manual-audits",
        json={
            "manual_job_id": manual_job["manual_job_id"],
            "bad_prompt_fragment_ref": "frag_001",
            "failure_type": "window_flipping_bug",
        },
    )
    assert audit_resp.status_code == 200
    audit = audit_resp.json()

    client.post(
        f"/attempts/{attempt['attempt_id']}/manual-audit",
        json={
            "manual_audit_id": audit["audit_id"],
            "failure_record_id": audit["failure_record_id"],
        },
    )

    patch_resp = client.post(f"/failures/{audit['failure_record_id']}/recover")
    assert patch_resp.status_code == 200


def test_reason_is_nonempty_string() -> None:
    """Each recommended patch should have a non-empty reason."""
    _seed_reason_case()
    with get_session() as session:
        req = RecommendRequest(failure_signature="object_rotation_error", limit=5)
        result = recommend_patches(session, req)
    assert len(result.recommended_patches) >= 1
    for patch in result.recommended_patches:
        assert isinstance(patch.reason, str)
        assert len(patch.reason) > 0


def test_matched_by_contains_known_values() -> None:
    """matched_by should contain values from the known set."""
    known_matchers = {
        "exact_signature", "same_category", "text_similarity",
        "object_type_match", "motion_model_match", "fragment_keyword",
        "accepted",
    }
    _seed_reason_case()
    with get_session() as session:
        req = RecommendRequest(failure_signature="object_rotation_error", limit=5)
        result = recommend_patches(session, req)
    for patch in result.recommended_patches:
        if isinstance(patch.matched_by, list):
            for m in patch.matched_by:
                assert m in known_matchers, f"Unknown matcher: {m}"
        else:
            assert patch.matched_by in known_matchers


def test_exact_signature_in_matched_by() -> None:
    """Exact signature match should include 'exact_signature' in matched_by."""
    _seed_reason_case()
    with get_session() as session:
        req = RecommendRequest(failure_signature="object_rotation_error", limit=5)
        result = recommend_patches(session, req)
    assert len(result.recommended_patches) >= 1
    top = result.recommended_patches[0]
    if isinstance(top.matched_by, list):
        assert "exact_signature" in top.matched_by
    else:
        assert top.matched_by == "exact_signature"


def test_reason_mentions_signature() -> None:
    """Reason for exact match should mention the failure signature."""
    _seed_reason_case()
    with get_session() as session:
        req = RecommendRequest(failure_signature="object_rotation_error", limit=5)
        result = recommend_patches(session, req)
    assert len(result.recommended_patches) >= 1
    top = result.recommended_patches[0]
    assert "object_rotation_error" in top.reason


def test_reason_with_object_type_context() -> None:
    """Reason should include object_type when matched."""
    _seed_reason_case()
    with get_session() as session:
        req = RecommendRequest(
            failure_signature="object_rotation_error",
            object_type="valve",
            limit=5,
        )
        result = recommend_patches(session, req)
    assert len(result.recommended_patches) >= 1
    top = result.recommended_patches[0]
    assert isinstance(top.reason, str)
    assert len(top.reason) > 0
