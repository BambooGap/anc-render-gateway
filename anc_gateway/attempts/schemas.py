from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from anc_gateway.core.schemas import PatchPacket, PromptSourceMap
from anc_gateway.manual.schemas import ManualVendorPlatform


class AttemptStatus(StrEnum):
    DRAFT = "DRAFT"
    COMPILED = "COMPILED"
    MANUAL_JOB_CREATED = "MANUAL_JOB_CREATED"
    VIDEO_COMPLETED = "VIDEO_COMPLETED"
    AUDITED = "AUDITED"
    PATCHED = "PATCHED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CaseCreateRequest(BaseModel):
    title: str | None = None
    raw_prompt: str
    platform: ManualVendorPlatform = ManualVendorPlatform.GENERIC_WEB
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseResponse(BaseModel):
    case_id: str
    title: str
    raw_prompt: str
    platform: ManualVendorPlatform
    current_attempt_id: str | None
    created_at: str | None
    updated_at: str | None


class AttemptCreateRequest(BaseModel):
    raw_prompt: str | None = None
    compiled_prompt: str | None = None
    condition_hash: str | None = None
    source_map: PromptSourceMap | None = None
    previous_attempt_id: str | None = None
    patch_packet: PatchPacket | dict[str, Any] | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttemptLinkManualJobRequest(BaseModel):
    manual_job_id: str
    result_video_uri: str | None = None


class AttemptLinkManualAuditRequest(BaseModel):
    manual_audit_id: str
    failure_record_id: str | None = None


class AttemptLinkPatchRequest(BaseModel):
    patch_packet: PatchPacket | dict[str, Any]
    patch_record_id: str | None = None


class AttemptResponse(BaseModel):
    attempt_id: str
    case_id: str
    attempt_index: int
    status: AttemptStatus
    raw_prompt: str
    compiled_prompt: str | None
    condition_hash: str | None
    manual_job_id: str | None
    manual_audit_id: str | None
    failure_record_id: str | None
    patch_record_id: str | None
    patch_prompt: str | None
    result_video_uri: str | None
    notes: str | None
    created_at: str | None
    updated_at: str | None
