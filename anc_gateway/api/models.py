from __future__ import annotations

from pydantic import BaseModel

from anc_gateway.core.schemas import (
    CompiledRenderPacket,
    FailureCacheRecord,
    RFSAuditResult,
    RenderContract,
    StateT,
)


class CompileRequest(BaseModel):
    state: StateT
    render_contract: RenderContract
    raw_prompt: str


class AuditRequest(BaseModel):
    audit: RFSAuditResult
    packet: CompiledRenderPacket


class RecoverRequest(BaseModel):
    failure_record: FailureCacheRecord
