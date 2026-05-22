from __future__ import annotations

from fastapi.testclient import TestClient

from anc_gateway.api.app import app

client = TestClient(app)


def _seed_data() -> None:
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_demo_cb_001", "shot_id": "shot_demo_cb_001", "objects": []},
            "render_contract": {"shot_id": "shot_demo_cb_001"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()

    case_response = client.post(
        "/cases",
        json={
            "title": "casebase-demo-case",
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


def test_casebase_demo_cli_runs(capsys: object) -> None:
    _seed_data()
    from anc_gateway.cli import casebase_demo

    casebase_demo()
    import sys
    captured = sys.stdout.getvalue() if hasattr(sys.stdout, "getvalue") else ""
    # The demo should output JSON with failure stats, search results, and recommendations
    assert "Failure Signature Stats" in captured or "object_rotation_error" in captured
