from __future__ import annotations

from fastapi.testclient import TestClient

from anc_gateway.api.app import app

client = TestClient(app)


def _seed_full_casebase_data() -> dict[str, object]:
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_api_cb_001", "shot_id": "shot_api_cb_001", "objects": []},
            "render_contract": {"shot_id": "shot_api_cb_001"},
            "raw_prompt": "她轻轻推开了推拉窗，冷白色应急灯照进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()

    case_response = client.post(
        "/cases",
        json={
            "title": "api-casebase-test",
            "raw_prompt": "她轻轻推开了推拉窗，冷白色应急灯照进房间。",
            "platform": "generic_web",
        },
    )
    assert case_response.status_code == 200
    case = case_response.json()

    attempt_response = client.post(
        f"/cases/{case['case_id']}/attempts",
        json={
            "raw_prompt": "她轻轻推开了推拉窗，冷白色应急灯照进房间。",
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

    return {"case": case, "attempt": attempt, "audit": audit}


def test_casebase_search_endpoint() -> None:
    _seed_full_casebase_data()
    response = client.get("/casebase/search?failure_signature=object_rotation_error")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)


def test_casebase_search_text_endpoint() -> None:
    _seed_full_casebase_data()
    response = client.get("/casebase/search?q=推拉窗")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)


def test_casebase_failure_stats_endpoint() -> None:
    _seed_full_casebase_data()
    response = client.get("/casebase/stats/failures")
    assert response.status_code == 200
    stats = response.json()
    assert isinstance(stats, list)
    assert len(stats) >= 1
    assert stats[0]["failure_signature"] == "object_rotation_error"


def test_casebase_patches_endpoint() -> None:
    _seed_full_casebase_data()
    response = client.get("/casebase/patches?limit=10")
    assert response.status_code == 200
    patches = response.json()
    assert isinstance(patches, list)


def test_casebase_recommend_endpoint() -> None:
    _seed_full_casebase_data()
    response = client.post(
        "/casebase/recommend-patches",
        json={"failure_signature": "object_rotation_error", "limit": 3},
    )
    assert response.status_code == 200
    result = response.json()
    assert "recommended_patches" in result
    assert "total_candidates" in result


def test_casebase_search_empty() -> None:
    response = client.get("/casebase/search?q=nonexistent_query_xyz")
    assert response.status_code == 200
    assert response.json() == []


def test_casebase_stats_empty() -> None:
    response = client.get("/casebase/stats/failures")
    assert response.status_code == 200
    assert response.json() == []


def test_casebase_patches_empty() -> None:
    response = client.get("/casebase/patches")
    assert response.status_code == 200
    assert response.json() == []
