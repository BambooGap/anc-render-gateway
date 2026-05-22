from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from anc_gateway.core.schemas import PromptSourceMap


class ManualJobStatus(StrEnum):
    WAITING_FOR_USER = "WAITING_FOR_USER"
    SUBMITTED_BY_USER = "SUBMITTED_BY_USER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ManualVendorPlatform(StrEnum):
    JIMENG_WEB = "jimeng_web"
    GEMINI_FLOW = "gemini_flow"
    GENERIC_WEB = "generic_web"


class ManualJobCreateRequest(BaseModel):
    condition_hash: str
    compiled_prompt: str
    source_map: PromptSourceMap
    platform: ManualVendorPlatform
    visual_anchor_uri: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ManualJobResponse(BaseModel):
    manual_job_id: str
    status: ManualJobStatus
    platform: ManualVendorPlatform
    condition_hash: str
    compiled_prompt: str
    copy_instructions: str
    visual_anchor_uri: str | None
    result_video_uri: str | None
    user_notes: str | None
    created_at: str | None
    updated_at: str | None


class CompleteManualJobRequest(BaseModel):
    result_video_uri: str
    user_notes: str | None = None
    status: ManualJobStatus = ManualJobStatus.COMPLETED

    @field_validator("result_video_uri")
    @classmethod
    def validate_result_video_uri(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("result_video_uri must be a non-empty string")
        return stripped


class FailManualJobRequest(BaseModel):
    user_notes: str | None = None
