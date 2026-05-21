from sqlalchemy import select

from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.storage.database import get_session
from anc_gateway.storage.models import (
    CompileJobModel,
    FailureRecordModel,
    GatewayTransactionModel,
    PatchRecordModel,
)


client = TestClient(app)


def test_api_compile_audit_recover_are_persisted() -> None:
    compile_response = client.post(
        "/compile",
        headers={"X-Request-ID": "req-persist-compile"},
        json={
            "state": {"id": "state_api_persist", "shot_id": "shot_api_persist", "objects": []},
            "render_contract": {"shot_id": "shot_api_persist"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()

    with get_session() as session:
        compile_jobs = list(session.scalars(select(CompileJobModel)))
        assert len(compile_jobs) == 1
        assert compile_jobs[0].condition_hash == packet["condition_hash"]
        transactions = list(session.scalars(select(GatewayTransactionModel)))
        assert len(transactions) == 1
        assert transactions[0].status == "compiled"

    audit_response = client.post(
        "/audit",
        headers={"X-Request-ID": "req-persist-audit"},
        json={
            "audit": {
                "ok": False,
                "raw_signature": "window_flipping_bug",
                "bad_prompt_fragment_ref": "frag_001",
            },
            "packet": packet,
        },
    )
    assert audit_response.status_code == 200
    failure_record = audit_response.json()
    assert failure_record["signature"] == "object_rotation_error"

    with get_session() as session:
        failure_records = list(session.scalars(select(FailureRecordModel)))
        assert len(failure_records) == 1
        assert failure_records[0].failure_signature == "object_rotation_error"

    recover_response = client.post(
        "/recover",
        headers={"X-Request-ID": "req-persist-recover"},
        json={"failure_record": failure_record},
    )
    assert recover_response.status_code == 200
    patch = recover_response.json()
    assert "窗扇保持垂直平面姿态" in patch["patch_prompt"]

    with get_session() as session:
        patch_records = list(session.scalars(select(PatchRecordModel)))
        assert len(patch_records) == 1
        assert patch_records[0].target_fragment_ref == "frag_001"


def test_recent_failures_endpoint_returns_persisted_records() -> None:
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_recent", "shot_id": "shot_recent", "objects": []},
            "render_contract": {"shot_id": "shot_recent"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    packet = compile_response.json()
    audit_response = client.post(
        "/audit",
        json={
            "audit": {
                "ok": False,
                "raw_signature": "window_flipping_bug",
                "bad_prompt_fragment_ref": "frag_001",
            },
            "packet": packet,
        },
    )
    assert audit_response.status_code == 200

    recent_response = client.get("/storage/recent-failures?limit=20")

    assert recent_response.status_code == 200
    recent_failures = recent_response.json()
    assert len(recent_failures) == 1
    assert recent_failures[0]["failure_signature"] == "object_rotation_error"
