"""Tests for casebase ranking API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from anc_gateway.api.app import app

client = TestClient(app)


def _seed_api_ranking() -> None:
    scenarios = [
        ("api-rank-valve", "阀门旋转时角度错误。", "window_flipping_bug"),
        ("api-rank-window", "推拉窗在轨道上滑动时翻转。", "window_flipping_bug"),
    ]
    for title, prompt, failure_type in scenarios:
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
            json={"title": title, "raw_prompt": prompt, "platform": "generic_web"},
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


def test_recommend_api_returns_ranking_fields() -> None:
    """API recommend endpoint should return ranking_score, reason, matched_by."""
    _seed_api_ranking()
    resp = client.post(
        "/casebase/recommend-patches",
        json={"failure_signature": "object_rotation_error", "limit": 5},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert len(result["recommended_patches"]) >= 1
    top = result["recommended_patches"][0]
    assert "ranking_score" in top
    assert "reason" in top
    assert "matched_by" in top
    assert "duplicate_count" in top
    assert "source_case_count" in top
    assert top["ranking_score"] > 0


def test_recommend_api_with_object_type() -> None:
    """API recommend with object_type parameter should work."""
    _seed_api_ranking()
    resp = client.post(
        "/casebase/recommend-patches",
        json={
            "failure_signature": "object_rotation_error",
            "object_type": "valve",
            "limit": 5,
        },
    )
    assert resp.status_code == 200
    result = resp.json()
    assert "recommended_patches" in result


def test_recommend_api_with_motion_model() -> None:
    """API recommend with motion_model parameter should work."""
    _seed_api_ranking()
    resp = client.post(
        "/casebase/recommend-patches",
        json={
            "failure_signature": "object_rotation_error",
            "motion_model": "center_axis_rotation",
            "limit": 5,
        },
    )
    assert resp.status_code == 200
    result = resp.json()
    assert "recommended_patches" in result


def test_recommend_api_with_all_context() -> None:
    """API recommend with all context parameters should work."""
    _seed_api_ranking()
    resp = client.post(
        "/casebase/recommend-patches",
        json={
            "failure_signature": "object_rotation_error",
            "object_type": "valve",
            "motion_model": "center_axis_rotation",
            "bad_prompt_fragment": "阀门",
            "limit": 5,
        },
    )
    assert resp.status_code == 200
    result = resp.json()
    assert len(result["recommended_patches"]) >= 1
    top = result["recommended_patches"][0]
    assert top["ranking_score"] > 0
    assert len(top["reason"]) > 0


def test_patches_endpoint_dedupe_param() -> None:
    """PATCHES endpoint with dedupe=true should work."""
    _seed_api_ranking()
    resp = client.get("/casebase/patches?limit=10&dedupe=true")
    assert resp.status_code == 200
    patches = resp.json()
    assert isinstance(patches, list)
    for p in patches:
        assert "duplicate_count" in p


def test_patches_endpoint_without_dedupe() -> None:
    """PATCHES endpoint without dedupe should also work."""
    _seed_api_ranking()
    resp = client.get("/casebase/patches?limit=10")
    assert resp.status_code == 200
    patches = resp.json()
    assert isinstance(patches, list)
