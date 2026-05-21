from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from anc_gateway.core.schemas import (
    CompiledRenderPacket,
    FailureCacheRecord,
    PatchPacket,
    RFSAuditResult,
    RenderContract,
    StateT,
)
from anc_gateway.storage.models import (
    CompileJobModel,
    FailureRecordModel,
    GatewayTransactionModel,
    ManualAuditModel,
    PatchRecordModel,
    PromptSourceMapRecordModel,
)
from anc_gateway.storage.serializers import (
    dumps_json,
    failure_record_to_json,
    model_to_json,
    patch_packet_to_json,
    source_map_to_json,
)


def get_or_create_gateway_transaction(
    session: Session,
    request_id: str | None = None,
    state_id: str | None = None,
    shot_id: str | None = None,
    status: str = "created",
) -> GatewayTransactionModel:
    transaction = None
    if request_id:
        transaction = session.scalar(
            select(GatewayTransactionModel).where(GatewayTransactionModel.request_id == request_id)
        )

    if transaction is None:
        transaction = GatewayTransactionModel(
            request_id=request_id,
            state_id=state_id,
            shot_id=shot_id,
            status=status,
        )
        session.add(transaction)
    else:
        transaction.status = status
        if state_id and not transaction.state_id:
            transaction.state_id = state_id
        if shot_id and not transaction.shot_id:
            transaction.shot_id = shot_id

    session.flush()
    return transaction


def save_compile_job(
    session: Session,
    raw_prompt: str,
    state: StateT,
    render_contract: RenderContract,
    packet: CompiledRenderPacket,
    request_id: str | None = None,
    transaction_id: str | None = None,
) -> CompileJobModel:
    model = CompileJobModel(
        transaction_id=transaction_id,
        request_id=request_id,
        raw_prompt=raw_prompt,
        compiled_prompt=packet.compiled_prompt,
        condition_hash=packet.condition_hash,
        ruleset_fingerprint=packet.ruleset_fingerprint,
        compiler_version=packet.compiler_version,
        state_json=dumps_json(model_to_json(state)),
        render_contract_json=dumps_json(model_to_json(render_contract)),
        source_map_json=dumps_json(source_map_to_json(packet.source_map)),
    )
    session.add(model)
    session.flush()
    for fragment in packet.source_map.fragments.values():
        session.add(
            PromptSourceMapRecordModel(
                compile_job_id=model.id,
                fragment_id=fragment.fragment_ref,
                original_text=fragment.original_text,
                rewritten_text=fragment.compiled_text,
                rules_applied=dumps_json({"rules_applied": fragment.rules_applied}),
            )
        )
    session.flush()
    return model


def get_compile_job_by_condition_hash(
    session: Session,
    condition_hash: str,
) -> CompileJobModel | None:
    return session.scalar(
        select(CompileJobModel).where(CompileJobModel.condition_hash == condition_hash)
    )


def save_failure_record(
    session: Session,
    record: FailureCacheRecord,
    audit: RFSAuditResult,
    condition_hash: str | None = None,
    ruleset_fingerprint: str = "unknown",
    request_id: str | None = None,
    transaction_id: str | None = None,
) -> FailureRecordModel:
    model = FailureRecordModel(
        transaction_id=transaction_id,
        request_id=request_id,
        condition_hash=condition_hash or record.packet_condition_hash,
        failure_signature=record.signature,
        failure_category=record.category,
        bad_prompt_fragment_ref=record.bad_prompt_fragment_ref,
        bad_prompt_fragment=record.bad_prompt_fragment,
        recovery_policy=record.recovery_policy,
        suggested_positive_lock=record.suggested_positive_lock,
        ruleset_fingerprint=ruleset_fingerprint,
        audit_json=dumps_json({"audit": model_to_json(audit), "record": failure_record_to_json(record)}),
    )
    session.add(model)
    session.flush()
    return model


def save_patch_record(
    session: Session,
    patch_packet: PatchPacket,
    failure_record_id: str | None = None,
    request_id: str | None = None,
    transaction_id: str | None = None,
) -> PatchRecordModel:
    model = PatchRecordModel(
        transaction_id=transaction_id,
        request_id=request_id,
        failure_record_id=failure_record_id,
        recovery_policy=patch_packet.recovery_policy,
        target_fragment_ref=patch_packet.target_fragment_ref,
        positive_lock=patch_packet.positive_lock,
        patch_packet_json=dumps_json(patch_packet_to_json(patch_packet)),
    )
    session.add(model)
    session.flush()
    return model


def list_recent_failures(session: Session, limit: int = 20) -> list[FailureRecordModel]:
    bounded_limit = max(1, min(limit, 100))
    return list(
        session.scalars(
            select(FailureRecordModel)
            .order_by(FailureRecordModel.created_at.desc())
            .limit(bounded_limit)
        )
    )


def get_failure_record_by_id(session: Session, failure_record_id: str) -> FailureRecordModel | None:
    return session.get(FailureRecordModel, failure_record_id)


def save_manual_audit(
    session: Session,
    *,
    request_id: str | None,
    manual_job_id: str | None,
    render_job_id: str | None,
    condition_hash: str | None,
    bad_prompt_fragment_ref: str,
    raw_failure_type: str,
    failure_signature: str,
    failure_category: str,
    recovery_policy: str | None,
    suggested_positive_lock: str | None,
    notes: str | None,
    rfs_scores: dict[str, object],
) -> ManualAuditModel:
    model = ManualAuditModel(
        request_id=request_id,
        manual_job_id=manual_job_id,
        render_job_id=render_job_id,
        condition_hash=condition_hash,
        bad_prompt_fragment_ref=bad_prompt_fragment_ref,
        raw_failure_type=raw_failure_type,
        failure_signature=failure_signature,
        failure_category=failure_category,
        recovery_policy=recovery_policy,
        suggested_positive_lock=suggested_positive_lock,
        notes=notes,
        rfs_scores_json=dumps_json(rfs_scores),
    )
    session.add(model)
    session.flush()
    return model


def list_recent_manual_audits(session: Session, limit: int = 20) -> list[ManualAuditModel]:
    bounded_limit = max(1, min(limit, 100))
    return list(
        session.scalars(
            select(ManualAuditModel).order_by(ManualAuditModel.created_at.desc()).limit(bounded_limit)
        )
    )
