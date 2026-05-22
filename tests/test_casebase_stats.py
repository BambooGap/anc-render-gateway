from __future__ import annotations

from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.casebase.stats import get_failure_signature_stats
from anc_gateway.storage.database import get_session

client = TestClient(app)


def _seed_case_with_failure() -> None:
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_stats_001", "shot_id": "shot_stats_001", "objects": []},
            "render_contract": {"shot_id": "shot_stats_001"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()

    case_response = client.post(
        "/cases",
        json={
            "title": "stats-test-case",
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


def test_failure_signature_stats_empty() -> None:
    with get_session() as session:
        stats = get_failure_signature_stats(session)
    assert stats == []


def test_failure_signature_stats_returns_counts() -> None:
    _seed_case_with_failure()
    with get_session() as session:
        stats = get_failure_signature_stats(session)
    assert len(stats) >= 1
    sig_stat = next(s for s in stats if s.failure_signature == "object_rotation_error")
    assert sig_stat.count >= 1
    assert sig_stat.latest_case_id is not None
    assert sig_stat.latest_case_title is not None


def test_failure_signature_stats_api_endpoint() -> None:
    _seed_case_with_failure()
    response = client.get("/casebase/stats/failures")
    assert response.status_code == 200
    stats = response.json()
    assert isinstance(stats, list)
    assert len(stats) >= 1
    assert stats[0]["failure_signature"] == "object_rotation_error"
