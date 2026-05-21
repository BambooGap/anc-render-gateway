from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from anc_gateway.api.models import AuditRequest, CompileRequest, HealthResponse, RecoverRequest
from anc_gateway.api.models import VersionResponse
from anc_gateway.api.request_context import get_request_id
from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import CompiledRenderPacket, FailureCacheRecord, PatchPacket
from anc_gateway.core.schemas import RenderContract
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
    get_or_create_gateway_transaction,
    list_recent_failures,
    save_compile_job,
    save_failure_record,
    save_patch_record,
)
from anc_gateway.vendors.capabilities import VendorCapability, get_vendor_capability
from anc_gateway.vendors.registry import default_vendor_registry

router = APIRouter()
logger = logging.getLogger(__name__)

SERVICE_NAME = "anc-render-gateway"
SERVICE_PHASE = "5A"
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
