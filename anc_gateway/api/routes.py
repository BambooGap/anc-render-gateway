from __future__ import annotations

from fastapi import APIRouter

from anc_gateway.api.models import AuditRequest, CompileRequest, HealthResponse, RecoverRequest
from anc_gateway.api.models import VersionResponse
from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import CompiledRenderPacket, FailureCacheRecord, PatchPacket
from anc_gateway.core.schemas import RenderContract
from anc_gateway.rfs.failure_normalizer import normalize_rfs_failure
from anc_gateway.recovery.patch_packet import build_patch_packet

router = APIRouter()

SERVICE_NAME = "anc-render-gateway"
SERVICE_PHASE = "2.5"
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


@router.post("/compile", response_model=CompiledRenderPacket)
def compile_endpoint(request: CompileRequest) -> CompiledRenderPacket:
    return compile_render_packet(
        request.state,
        request.render_contract,
        request.raw_prompt,
    )


@router.post("/audit", response_model=FailureCacheRecord | None)
def audit_endpoint(request: AuditRequest) -> FailureCacheRecord | None:
    if request.audit.ok:
        return None

    return normalize_rfs_failure(request.audit, request.packet)


@router.post("/recover", response_model=PatchPacket)
def recover_endpoint(request: RecoverRequest) -> PatchPacket:
    return build_patch_packet(request.failure_record)
