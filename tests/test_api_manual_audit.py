from sqlalchemy import select

from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.storage.database import get_session
from anc_gateway.storage.models import FailureRecordModel, ManualAuditModel


client = TestClient(app)


def _create_manual_job() -> dict[str, object]:
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_api_manual_audit", "shot_id": "shot_api_manual_audit", "objects": []},
            "render_contract": {"shot_id": "shot_api_manual_audit"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()
    manual_response = client.post(
        "/manual-jobs",
        json={
            "condition_hash": packet["condition_hash"],
            "compiled_prompt": packet["compiled_prompt"],
            "source_map": packet["source_map"],
            "platform": "generic_web",
        },
    )
    assert manual_response.status_code == 200
    return manual_response.json()


def test_post_manual_audit_creates_audit_and_failure_record() -> None:
    manual_job = _create_manual_job()

    response = client.post(
        "/manual-audits",
        json={
            "manual_job_id": manual_job["manual_job_id"],
            "bad_prompt_fragment_ref": "frag_001",
            "failure_type": "window_flipping_bug",
            "notes": "窗户翻转。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["failure_signature"] == "window_flipping_bug"
    assert payload["normalized_failure_signature"] == "object_rotation_error"
    assert payload["failure_category"] == "topology_dof_violation"
    assert payload["recovery_policy"] == "LEVEL_2_NEGATIVE_MITIGATION"
    assert payload["suggested_positive_lock"]
    assert payload["failure_record_id"]

    with get_session() as session:
        manual_audits = list(session.scalars(select(ManualAuditModel)))
        failure_records = list(session.scalars(select(FailureRecordModel)))

    assert len(manual_audits) == 1
    assert len(failure_records) == 1
    assert failure_records[0].failure_signature == "object_rotation_error"


def test_manual_audit_hand_contact_normalizes() -> None:
    manual_job = _create_manual_job()

    response = client.post(
        "/manual-audits",
        json={
            "manual_job_id": manual_job["manual_job_id"],
            "bad_prompt_fragment_ref": "frag_001",
            "failure_type": "hand_not_touching_panel",
            "notes": "手没有接触面板。",
        },
    )

    assert response.status_code == 200
    assert response.json()["normalized_failure_signature"] == "hand_panel_misalignment"


def test_manual_audit_bad_fragment_returns_structured_error() -> None:
    manual_job = _create_manual_job()

    response = client.post(
        "/manual-audits",
        headers={"X-Request-ID": "req-manual-audit-error"},
        json={
            "manual_job_id": manual_job["manual_job_id"],
            "bad_prompt_fragment_ref": "frag_999",
            "failure_type": "window_flipping_bug",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "SOURCE_MAP_ATTRIBUTION_ERROR"
    assert payload["error"]["request_id"] == "req-manual-audit-error"


def test_recent_manual_audits_returns_list() -> None:
    manual_job = _create_manual_job()
    response = client.post(
        "/manual-audits",
        json={
            "manual_job_id": manual_job["manual_job_id"],
            "bad_prompt_fragment_ref": "frag_001",
            "failure_type": "window_flipping_bug",
        },
    )
    assert response.status_code == 200

    recent_response = client.get("/manual-audits/recent?limit=20")

    assert recent_response.status_code == 200
    recent = recent_response.json()
    assert len(recent) == 1
    assert recent[0]["normalized_failure_signature"] == "object_rotation_error"
