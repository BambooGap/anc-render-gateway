from __future__ import annotations

from fastapi import APIRouter, HTTPException

from anc_gateway.api.models import AuditRequest, CompileRequest, RecoverRequest
from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import CompiledRenderPacket, FailureCacheRecord, PatchPacket
from anc_gateway.core.source_map import SourceMapAttributionError
from anc_gateway.rfs.failure_normalizer import normalize_rfs_failure
from anc_gateway.recovery.patch_packet import build_patch_packet

router = APIRouter()


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

    try:
        return normalize_rfs_failure(request.audit, request.packet)
    except SourceMapAttributionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/recover", response_model=PatchPacket)
def recover_endpoint(request: RecoverRequest) -> PatchPacket:
    return build_patch_packet(request.failure_record)
