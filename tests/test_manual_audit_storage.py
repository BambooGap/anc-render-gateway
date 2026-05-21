from sqlalchemy import select

from anc_gateway.audit.manual_audit import build_rfs_audit_from_manual_request
from anc_gateway.audit.schemas import ManualAuditCreateRequest
from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT
from anc_gateway.rfs.failure_normalizer import normalize_rfs_failure
from anc_gateway.storage.database import get_session
from anc_gateway.storage.models import ManualAuditModel
from anc_gateway.storage.repositories import list_recent_manual_audits, save_manual_audit


def test_save_manual_audit_and_list_recent() -> None:
    packet = compile_render_packet(
        StateT(id="state_manual_audit_storage", shot_id="shot_manual_audit_storage"),
        RenderContract(shot_id="shot_manual_audit_storage"),
        "她轻轻推开了推拉窗，风吹进房间。",
    )
    request = ManualAuditCreateRequest(
        condition_hash=packet.condition_hash,
        bad_prompt_fragment_ref="frag_001",
        failure_type="window_flipping_bug",
        notes="窗户翻转。",
    )
    audit = build_rfs_audit_from_manual_request(request)
    record = normalize_rfs_failure(audit, packet)

    with get_session() as session:
        saved = save_manual_audit(
            session,
            request_id="req-manual-audit-storage",
            manual_job_id=None,
            render_job_id=None,
            condition_hash=packet.condition_hash,
            bad_prompt_fragment_ref=request.bad_prompt_fragment_ref,
            raw_failure_type=request.failure_type,
            failure_signature=record.signature,
            failure_category=record.category,
            recovery_policy=record.recovery_policy,
            suggested_positive_lock=record.suggested_positive_lock,
            notes=request.notes,
            rfs_scores=audit.details["rfs_scores"],
        )
        saved_id = saved.id

    with get_session() as session:
        audits = list_recent_manual_audits(session, limit=20)
        stored = session.scalar(select(ManualAuditModel).where(ManualAuditModel.id == saved_id))

    assert len(audits) == 1
    assert stored is not None
    assert stored.failure_signature == "object_rotation_error"
    assert stored.failure_category == "topology_dof_violation"
