from __future__ import annotations

from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.casebase.search import search_casebase
from anc_gateway.storage.database import get_session

client = TestClient(app)


def _seed_case_with_failure() -> dict[str, object]:
    """Create a case with attempt + failure record via API."""
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_search_001", "shot_id": "shot_search_001", "objects": []},
            "render_contract": {"shot_id": "shot_search_001"},
            "raw_prompt": "她轻轻推开了推拉窗，冷白色应急灯照进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()

    case_response = client.post(
        "/cases",
        json={
            "title": "search-test-case",
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

    return {"case": case, "attempt": attempt, "audit": audit}


def test_search_casebase_returns_empty_without_data() -> None:
    with get_session() as session:
        results = search_casebase(session, q="nonexistent", limit=10)
    assert results == []


def test_search_casebase_by_failure_signature() -> None:
    _seed_case_with_failure()
    with get_session() as session:
        results = search_casebase(session, failure_signature="object_rotation_error", limit=10)
    assert len(results) >= 1
    assert results[0].failure_signature == "object_rotation_error"


def test_search_casebase_by_failure_category() -> None:
    _seed_case_with_failure()
    with get_session() as session:
        results = search_casebase(session, failure_category="topology_dof_violation", limit=10)
    assert len(results) >= 1


def test_search_casebase_by_text_query() -> None:
    _seed_case_with_failure()
    with get_session() as session:
        results = search_casebase(session, q="推拉窗", limit=10)
    assert len(results) >= 1


def test_search_casebase_respects_limit() -> None:
    _seed_case_with_failure()
    with get_session() as session:
        results = search_casebase(session, limit=1)
    assert len(results) <= 1


def test_search_casebase_api_endpoint() -> None:
    _seed_case_with_failure()
    response = client.get("/casebase/search?q=推拉窗&limit=10")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) >= 1
