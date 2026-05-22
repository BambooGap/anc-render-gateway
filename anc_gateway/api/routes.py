from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from anc_gateway.attempts.job_manager import (
    attempt_to_response,
    case_to_response,
    create_attempt,
    create_case,
    get_attempt,
    get_case,
    link_attempt_manual_audit,
    link_attempt_manual_job,
    link_attempt_patch,
    list_case_attempts,
    list_recent_cases,
)
from anc_gateway.attempts.schemas import (
    AttemptCreateRequest,
    AttemptLinkManualAuditRequest,
    AttemptLinkManualJobRequest,
    AttemptLinkPatchRequest,
    AttemptResponse,
    CaseCreateRequest,
    CaseResponse,
)
from anc_gateway.audit.manual_audit import build_rfs_audit_from_manual_request
from anc_gateway.audit.schemas import ManualAuditCreateRequest, ManualAuditResponse
from anc_gateway.api.models import AuditRequest, CompileRequest, HealthResponse, RecoverRequest
from anc_gateway.api.models import VersionResponse
from anc_gateway.api.request_context import get_request_id
from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import (
    CompiledRenderPacket,
    FailureCacheRecord,
    PatchPacket,
    PromptSourceMap,
)
from anc_gateway.core.schemas import RenderContract
from anc_gateway.manual.job_manager import (
    complete_manual_job,
    create_manual_job,
    fail_manual_job,
    get_manual_job,
    list_recent_manual_jobs,
    manual_job_to_response,
)
from anc_gateway.manual.schemas import (
    CompleteManualJobRequest,
    FailManualJobRequest,
    ManualJobCreateRequest,
    ManualJobResponse,
)
from anc_gateway.render.job_manager import (
    create_render_job,
    get_render_job,
    list_recent_render_jobs,
    render_job_to_response,
    submit_render_job_to_vendor,
)
from anc_gateway.render.mock_worker import fail_mock_render, run_mock_render
from anc_gateway.render.schemas import (
    RenderJobCreateRequest,
    RenderJobFailRequest,
    RenderJobResponse,
)
from anc_gateway.rfs.failure_normalizer import normalize_rfs_failure
from anc_gateway.recovery.patch_packet import build_patch_packet
from anc_gateway.storage.database import get_session
from anc_gateway.storage.repositories import (
    get_compile_job_by_condition_hash,
    get_failure_record_by_id,
    get_or_create_gateway_transaction,
    list_recent_manual_audits,
    list_recent_failures,
    save_compile_job,
    save_failure_record,
    save_manual_audit,
    save_patch_record,
)
from anc_gateway.vendors.capabilities import VendorCapability, get_vendor_capability
from anc_gateway.vendors.registry import default_vendor_registry

router = APIRouter()
logger = logging.getLogger(__name__)

SERVICE_NAME = "anc-render-gateway"
SERVICE_PHASE = "6B"
DEFAULT_RENDER_CONTRACT = RenderContract(shot_id="default")


@router.get("/health", response_model=HealthResponse)
def health_endpoint() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/version", response_model=VersionResponse)
def version_endpoint() -> VersionResponse:
    return VersionResponse(
        service=SERVICE_NAME,
        phase=SERVICE_PHASE,
        compiler_version=DEFAULT_RENDER_CONTRACT.compiler_version,
        ruleset_fingerprint=DEFAULT_RENDER_CONTRACT.ruleset_fingerprint,
    )


@router.get("/vendors", response_model=list[str])
def vendors_endpoint() -> list[str]:
    return default_vendor_registry.list_vendors()


@router.get("/vendors/{vendor}/capabilities", response_model=VendorCapability)
def vendor_capabilities_endpoint(vendor: str) -> VendorCapability:
    if not default_vendor_registry.has(vendor):
        raise ValueError(f"Unknown render vendor: {vendor}")
    return get_vendor_capability(vendor)


@router.post("/cases", response_model=CaseResponse)
def create_case_endpoint(request: Request, payload: CaseCreateRequest) -> CaseResponse:
    with get_session() as session:
        case = create_case(session, payload, request_id=get_request_id(request))
        return case_to_response(case)


@router.get("/cases/recent", response_model=list[CaseResponse])
def recent_cases_endpoint(limit: int = 20) -> list[CaseResponse]:
    with get_session() as session:
        return [case_to_response(case) for case in list_recent_cases(session, limit=limit)]


@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case_endpoint(case_id: str) -> CaseResponse:
    with get_session() as session:
        case = get_case(session, case_id)
        if case is None:
            raise ValueError(f"Case not found: {case_id}")
        return case_to_response(case)


@router.post("/cases/{case_id}/attempts", response_model=AttemptResponse)
def create_attempt_endpoint(
    request: Request,
    case_id: str,
    payload: AttemptCreateRequest,
) -> AttemptResponse:
    with get_session() as session:
        case = get_case(session, case_id)
        if case is None:
            raise ValueError(f"Case not found: {case_id}")
        attempt = create_attempt(session, case, payload, request_id=get_request_id(request))
        return attempt_to_response(attempt)


@router.get("/cases/{case_id}/attempts", response_model=list[AttemptResponse])
def list_case_attempts_endpoint(case_id: str) -> list[AttemptResponse]:
    with get_session() as session:
        case = get_case(session, case_id)
        if case is None:
            raise ValueError(f"Case not found: {case_id}")
        return [attempt_to_response(attempt) for attempt in list_case_attempts(session, case_id)]


@router.get("/attempts/{attempt_id}", response_model=AttemptResponse)
def get_attempt_endpoint(attempt_id: str) -> AttemptResponse:
    with get_session() as session:
        attempt = get_attempt(session, attempt_id)
        if attempt is None:
            raise ValueError(f"Attempt not found: {attempt_id}")
        return attempt_to_response(attempt)


@router.post("/attempts/{attempt_id}/manual-job", response_model=AttemptResponse)
def link_attempt_manual_job_endpoint(
    attempt_id: str,
    payload: AttemptLinkManualJobRequest,
) -> AttemptResponse:
    with get_session() as session:
        attempt = get_attempt(session, attempt_id)
        if attempt is None:
            raise ValueError(f"Attempt not found: {attempt_id}")
        return attempt_to_response(
            link_attempt_manual_job(
                session,
                attempt,
                manual_job_id=payload.manual_job_id,
                result_video_uri=payload.result_video_uri,
            )
        )


@router.post("/attempts/{attempt_id}/manual-audit", response_model=AttemptResponse)
def link_attempt_manual_audit_endpoint(
    attempt_id: str,
    payload: AttemptLinkManualAuditRequest,
) -> AttemptResponse:
    with get_session() as session:
        attempt = get_attempt(session, attempt_id)
        if attempt is None:
            raise ValueError(f"Attempt not found: {attempt_id}")
        return attempt_to_response(
            link_attempt_manual_audit(
                session,
                attempt,
                manual_audit_id=payload.manual_audit_id,
                failure_record_id=payload.failure_record_id,
            )
        )


@router.post("/attempts/{attempt_id}/patch", response_model=AttemptResponse)
def link_attempt_patch_endpoint(
    attempt_id: str,
    payload: AttemptLinkPatchRequest,
) -> AttemptResponse:
    with get_session() as session:
        attempt = get_attempt(session, attempt_id)
        if attempt is None:
            raise ValueError(f"Attempt not found: {attempt_id}")
        patch_prompt = _extract_patch_prompt(payload.patch_packet)
        return attempt_to_response(
            link_attempt_patch(
                session,
                attempt,
                patch_prompt=patch_prompt,
                patch_record_id=payload.patch_record_id,
            )
        )


@router.post("/compile", response_model=CompiledRenderPacket)
def compile_endpoint(request: Request, payload: CompileRequest) -> CompiledRenderPacket:
    packet = compile_render_packet(
        payload.state,
        payload.render_contract,
        payload.raw_prompt,
    )
    try:
        with get_session() as session:
            transaction = get_or_create_gateway_transaction(
                session,
                request_id=get_request_id(request),
                state_id=payload.state.id,
                shot_id=payload.render_contract.shot_id,
                status="compiled",
            )
            save_compile_job(
                session,
                raw_prompt=payload.raw_prompt,
                state=payload.state,
                render_contract=payload.render_contract,
                packet=packet,
                request_id=get_request_id(request),
                transaction_id=transaction.id,
            )
    except Exception:
        logger.warning("Failed to persist compile job", exc_info=True)
    return packet


@router.post("/audit", response_model=FailureCacheRecord | None)
def audit_endpoint(request: Request, payload: AuditRequest) -> FailureCacheRecord | None:
    if payload.audit.ok:
        return None

    record = normalize_rfs_failure(payload.audit, payload.packet)
    try:
        with get_session() as session:
            transaction = get_or_create_gateway_transaction(
                session,
                request_id=get_request_id(request),
                state_id=payload.packet.state_id,
                shot_id=payload.packet.shot_id,
                status="failed",
            )
            save_failure_record(
                session,
                record,
                payload.audit,
                condition_hash=payload.packet.condition_hash,
                ruleset_fingerprint=payload.packet.ruleset_fingerprint,
                request_id=get_request_id(request),
                transaction_id=transaction.id,
            )
    except Exception:
        logger.warning("Failed to persist failure record", exc_info=True)
    return record


@router.post("/recover", response_model=PatchPacket)
def recover_endpoint(request: Request, payload: RecoverRequest) -> PatchPacket:
    patch = build_patch_packet(payload.failure_record)
    try:
        with get_session() as session:
            transaction = get_or_create_gateway_transaction(
                session,
                request_id=get_request_id(request),
                status="recovered",
            )
            save_patch_record(
                session,
                patch,
                request_id=get_request_id(request),
                transaction_id=transaction.id,
            )
    except Exception:
        logger.warning("Failed to persist patch record", exc_info=True)
    return patch


@router.post("/failures/{failure_record_id}/recover", response_model=PatchPacket)
def recover_failure_endpoint(request: Request, failure_record_id: str) -> PatchPacket:
    with get_session() as session:
        failure = get_failure_record_by_id(session, failure_record_id)
        if failure is None:
            raise ValueError(f"Failure record not found: {failure_record_id}")
        record = FailureCacheRecord(
            category=failure.failure_category,
            signature=failure.failure_signature,
            raw_signature=failure.failure_signature,
            recovery_policy=failure.recovery_policy,
            bad_prompt_fragment_ref=failure.bad_prompt_fragment_ref,
            bad_prompt_fragment=failure.bad_prompt_fragment,
            suggested_positive_lock=failure.suggested_positive_lock,
            packet_condition_hash=failure.condition_hash or "",
        )
        patch = build_patch_packet(record)
        transaction = get_or_create_gateway_transaction(
            session,
            request_id=get_request_id(request),
            status="recovered",
        )
        save_patch_record(
            session,
            patch,
            failure_record_id=failure.id,
            request_id=get_request_id(request),
            transaction_id=transaction.id,
        )
        return patch


@router.get("/storage/recent-failures")
def recent_failures_endpoint(limit: int = 20) -> list[dict[str, str | None]]:
    with get_session() as session:
        records = list_recent_failures(session, limit=limit)
        return [
            {
                "failure_signature": record.failure_signature,
                "failure_category": record.failure_category,
                "bad_prompt_fragment": record.bad_prompt_fragment,
                "recovery_policy": record.recovery_policy,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
            for record in records
        ]


@router.post("/render-jobs", response_model=RenderJobResponse)
def create_render_job_endpoint(
    request: Request,
    payload: RenderJobCreateRequest,
) -> RenderJobResponse:
    with get_session() as session:
        job = create_render_job(session, payload, request_id=get_request_id(request))
        return render_job_to_response(job)


@router.get("/render-jobs/recent", response_model=list[RenderJobResponse])
def recent_render_jobs_endpoint(limit: int = 20) -> list[RenderJobResponse]:
    with get_session() as session:
        return [render_job_to_response(job) for job in list_recent_render_jobs(session, limit=limit)]


@router.get("/render-jobs/{job_id}", response_model=RenderJobResponse)
def get_render_job_endpoint(job_id: str) -> RenderJobResponse:
    with get_session() as session:
        job = get_render_job(session, job_id)
        if job is None:
            raise ValueError(f"Render job not found: {job_id}")
        return render_job_to_response(job)


@router.post("/render-jobs/{job_id}/run-mock", response_model=RenderJobResponse)
def run_mock_render_endpoint(job_id: str) -> RenderJobResponse:
    with get_session() as session:
        job = get_render_job(session, job_id)
        if job is None:
            raise ValueError(f"Render job not found: {job_id}")
        return render_job_to_response(run_mock_render(session, job))


@router.post("/render-jobs/{job_id}/fail-mock", response_model=RenderJobResponse)
def fail_mock_render_endpoint(
    job_id: str,
    payload: RenderJobFailRequest | None = None,
) -> RenderJobResponse:
    with get_session() as session:
        job = get_render_job(session, job_id)
        if job is None:
            raise ValueError(f"Render job not found: {job_id}")
        return render_job_to_response(
            fail_mock_render(
                session,
                job,
                error_message=payload.error_message if payload else None,
            )
        )


@router.post("/render-jobs/{job_id}/submit-vendor", response_model=RenderJobResponse)
def submit_vendor_render_endpoint(job_id: str) -> RenderJobResponse:
    with get_session() as session:
        job = get_render_job(session, job_id)
        if job is None:
            raise ValueError(f"Render job not found: {job_id}")
        return render_job_to_response(submit_render_job_to_vendor(session, job))


@router.post("/manual-jobs", response_model=ManualJobResponse)
def create_manual_job_endpoint(
    request: Request,
    payload: ManualJobCreateRequest,
) -> ManualJobResponse:
    with get_session() as session:
        job = create_manual_job(session, payload, request_id=get_request_id(request))
        return manual_job_to_response(job)


@router.get("/manual-jobs/recent", response_model=list[ManualJobResponse])
def recent_manual_jobs_endpoint(limit: int = 20) -> list[ManualJobResponse]:
    with get_session() as session:
        return [manual_job_to_response(job) for job in list_recent_manual_jobs(session, limit=limit)]


@router.get("/manual-jobs/{manual_job_id}", response_model=ManualJobResponse)
def get_manual_job_endpoint(manual_job_id: str) -> ManualJobResponse:
    with get_session() as session:
        job = get_manual_job(session, manual_job_id)
        if job is None:
            raise ValueError(f"Manual job not found: {manual_job_id}")
        return manual_job_to_response(job)


@router.post("/manual-jobs/{manual_job_id}/complete", response_model=ManualJobResponse)
def complete_manual_job_endpoint(
    manual_job_id: str,
    payload: CompleteManualJobRequest,
) -> ManualJobResponse:
    with get_session() as session:
        job = get_manual_job(session, manual_job_id)
        if job is None:
            raise ValueError(f"Manual job not found: {manual_job_id}")
        return manual_job_to_response(complete_manual_job(session, job, payload))


@router.post("/manual-jobs/{manual_job_id}/fail", response_model=ManualJobResponse)
def fail_manual_job_endpoint(
    manual_job_id: str,
    payload: FailManualJobRequest | None = None,
) -> ManualJobResponse:
    with get_session() as session:
        job = get_manual_job(session, manual_job_id)
        if job is None:
            raise ValueError(f"Manual job not found: {manual_job_id}")
        return manual_job_to_response(
            fail_manual_job(session, job, user_notes=payload.user_notes if payload else None)
        )


@router.post("/manual-audits", response_model=ManualAuditResponse)
def create_manual_audit_endpoint(
    request: Request,
    payload: ManualAuditCreateRequest,
) -> ManualAuditResponse:
    with get_session() as session:
        packet = _resolve_packet_for_manual_audit(session, payload)
        audit = build_rfs_audit_from_manual_request(payload)
        record = normalize_rfs_failure(audit, packet)
        failure = save_failure_record(
            session,
            record,
            audit,
            condition_hash=packet.condition_hash,
            ruleset_fingerprint=packet.ruleset_fingerprint,
            request_id=get_request_id(request),
        )
        rfs_scores = audit.details.get("rfs_scores", {})
        manual_audit = save_manual_audit(
            session,
            request_id=get_request_id(request),
            manual_job_id=payload.manual_job_id,
            render_job_id=payload.render_job_id,
            condition_hash=packet.condition_hash,
            bad_prompt_fragment_ref=payload.bad_prompt_fragment_ref,
            raw_failure_type=payload.failure_type,
            failure_signature=record.signature,
            failure_category=record.category,
            recovery_policy=record.recovery_policy,
            suggested_positive_lock=record.suggested_positive_lock,
            notes=payload.notes,
            rfs_scores=rfs_scores if isinstance(rfs_scores, dict) else {},
        )
        return ManualAuditResponse(
            audit_id=manual_audit.id,
            passed=False,
            failure_signature=record.raw_signature,
            failure_category=record.category,
            bad_prompt_fragment_ref=record.bad_prompt_fragment_ref,
            normalized_failure_signature=record.signature,
            recovery_policy=record.recovery_policy,
            suggested_positive_lock=record.suggested_positive_lock,
            notes=payload.notes,
            created_at=manual_audit.created_at.isoformat() if manual_audit.created_at else None,
            failure_record_id=failure.id,
        )


@router.get("/manual-audits/recent", response_model=list[ManualAuditResponse])
def recent_manual_audits_endpoint(limit: int = 20) -> list[ManualAuditResponse]:
    with get_session() as session:
        return [
            ManualAuditResponse(
                audit_id=audit.id,
                passed=False,
                failure_signature=audit.raw_failure_type,
                failure_category=audit.failure_category,
                bad_prompt_fragment_ref=audit.bad_prompt_fragment_ref,
                normalized_failure_signature=audit.failure_signature,
                recovery_policy=audit.recovery_policy,
                suggested_positive_lock=audit.suggested_positive_lock,
                notes=audit.notes,
                created_at=audit.created_at.isoformat() if audit.created_at else None,
                failure_record_id=None,
            )
            for audit in list_recent_manual_audits(session, limit=limit)
        ]


def _resolve_packet_for_manual_audit(
    session: Session,
    payload: ManualAuditCreateRequest,
) -> CompiledRenderPacket:
    if payload.manual_job_id:
        manual_job = get_manual_job(session, payload.manual_job_id)
        if manual_job is None:
            raise ValueError(f"Manual job not found: {payload.manual_job_id}")
        return _packet_from_saved_fields(
            state_id="manual_job",
            shot_id=manual_job.id,
            compiled_prompt=manual_job.compiled_prompt,
            source_map_json=manual_job.source_map_json,
            condition_hash=manual_job.condition_hash,
            ruleset_fingerprint="manual",
            compiler_version=DEFAULT_RENDER_CONTRACT.compiler_version,
        )
    if payload.render_job_id:
        render_job = get_render_job(session, payload.render_job_id)
        if render_job is None:
            raise ValueError(f"Render job not found: {payload.render_job_id}")
        return _packet_from_saved_fields(
            state_id="render_job",
            shot_id=render_job.id,
            compiled_prompt=render_job.compiled_prompt,
            source_map_json=render_job.source_map_json,
            condition_hash=render_job.condition_hash,
            ruleset_fingerprint="render",
            compiler_version=DEFAULT_RENDER_CONTRACT.compiler_version,
        )
    if payload.condition_hash:
        compile_job = get_compile_job_by_condition_hash(session, payload.condition_hash)
        if compile_job is None:
            raise ValueError(f"Compile job not found for condition_hash: {payload.condition_hash}")
        state_payload = json.loads(compile_job.state_json)
        render_contract_payload = json.loads(compile_job.render_contract_json)
        return _packet_from_saved_fields(
            state_id=str(state_payload.get("id", "unknown")),
            shot_id=str(render_contract_payload.get("shot_id", "unknown")),
            compiled_prompt=compile_job.compiled_prompt,
            source_map_json=compile_job.source_map_json,
            condition_hash=compile_job.condition_hash,
            ruleset_fingerprint=compile_job.ruleset_fingerprint,
            compiler_version=compile_job.compiler_version,
        )
    raise ValueError("manual_job_id, render_job_id, or condition_hash is required")


def _packet_from_saved_fields(
    *,
    state_id: str,
    shot_id: str,
    compiled_prompt: str,
    source_map_json: str,
    condition_hash: str,
    ruleset_fingerprint: str,
    compiler_version: str,
) -> CompiledRenderPacket:
    source_map = PromptSourceMap.model_validate(json.loads(source_map_json))
    return CompiledRenderPacket(
        state_id=state_id,
        shot_id=shot_id,
        compiled_prompt=compiled_prompt,
        source_map=source_map,
        condition_hash=condition_hash,
        ruleset_fingerprint=ruleset_fingerprint,
        compiler_version=compiler_version,
    )


def _extract_patch_prompt(patch_packet: PatchPacket | dict[str, object]) -> str:
    if isinstance(patch_packet, PatchPacket):
        return patch_packet.patch_prompt or patch_packet.positive_lock
    for key in ("patch_prompt", "positive_lock", "suggested_positive_lock"):
        value = patch_packet.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return json.dumps(patch_packet, ensure_ascii=False, sort_keys=True)
