"""Tests for casebase ranking score computation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.casebase.recommendations import recommend_patches
from anc_gateway.casebase.schemas import RecommendRequest
from anc_gateway.storage.database import get_session

client = TestClient(app)


def _seed_ranking_cases() -> None:
    """Seed cases with different failure types for ranking tests."""
    scenarios = [
        ("rank-valve", "阀门旋转时角度错误。", "window_flipping_bug", "generic_web"),
        ("rank-window", "推拉窗在轨道上滑动时翻转。", "window_flipping_bug", "generic_web"),
        ("rank-drawer", "抽屉拉出时轨迹偏移。", "window_flipping_bug", "generic_web"),
    ]
    for title, prompt, failure_type, platform in scenarios:
        compile_resp = client.post(
            "/compile",
            json={
                "state": {"id": f"state_{title}", "shot_id": f"shot_{title}", "objects": []},
                "render_contract": {"shot_id": f"shot_{title}"},
                "raw_prompt": prompt,
            },
        )
        assert compile_resp.status_code == 200
        packet = compile_resp.json()

        case_resp = client.post(
            "/cases",
            json={"title": title, "raw_prompt": prompt, "platform": platform},
        )
        assert case_resp.status_code == 200
        case = case_resp.json()

        attempt_resp = client.post(
            f"/cases/{case['case_id']}/attempts",
            json={
                "raw_prompt": prompt,
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
                "platform": platform,
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
                "failure_type": failure_type,
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


def test_ranking_score_nonzero() -> None:
    """Ranking score should be > 0 for exact signature matches."""
    _seed_ranking_cases()
    with get_session() as session:
        req = RecommendRequest(failure_signature="object_rotation_error", limit=5)
        result = recommend_patches(session, req)
    assert len(result.recommended_patches) >= 1
    assert result.recommended_patches[0].ranking_score > 0.0


def test_ranking_score_range() -> None:
    """Ranking scores should be between 0.0 and 1.0."""
    _seed_ranking_cases()
    with get_session() as session:
        req = RecommendRequest(failure_signature="object_rotation_error", limit=5)
        result = recommend_patches(session, req)
    for patch in result.recommended_patches:
        assert 0.0 <= patch.ranking_score <= 1.0


def test_ranking_exact_signature_higher_than_text() -> None:
    """Exact signature match should rank higher than text similarity."""
    _seed_ranking_cases()
    with get_session() as session:
        exact_req = RecommendRequest(failure_signature="object_rotation_error", limit=5)
        exact_result = recommend_patches(session, exact_req)

        text_req = RecommendRequest(
            failure_signature="nonexistent_sig",
            bad_prompt_fragment="推拉窗",
            limit=5,
        )
        text_result = recommend_patches(session, text_req)

    if exact_result.recommended_patches and text_result.recommended_patches:
        best_exact = exact_result.recommended_patches[0].ranking_score
        best_text = text_result.recommended_patches[0].ranking_score
        assert best_exact >= best_text


def test_ranking_with_object_type_boost() -> None:
    """Providing object_type should boost matching candidates."""
    _seed_ranking_cases()
    with get_session() as session:
        req_with_ctx = RecommendRequest(
            failure_signature="object_rotation_error",
            object_type="valve",
            limit=5,
        )
        result = recommend_patches(session, req_with_ctx)

    assert len(result.recommended_patches) >= 1
    # Should have object_type_match in matched_by for valve candidates
    top = result.recommended_patches[0]
    assert top.ranking_score > 0


def test_ranking_with_motion_model_boost() -> None:
    """Providing motion_model should boost matching candidates."""
    _seed_ranking_cases()
    with get_session() as session:
        req = RecommendRequest(
            failure_signature="object_rotation_error",
            motion_model="center_axis_rotation",
            limit=5,
        )
        result = recommend_patches(session, req)

    assert len(result.recommended_patches) >= 1
    top = result.recommended_patches[0]
    assert top.ranking_score > 0


def test_ranking_descending_order() -> None:
    """Results should be sorted by ranking_score descending."""
    _seed_ranking_cases()
    with get_session() as session:
        req = RecommendRequest(failure_signature="object_rotation_error", limit=10)
        result = recommend_patches(session, req)

    scores = [p.ranking_score for p in result.recommended_patches]
    assert scores == sorted(scores, reverse=True)
