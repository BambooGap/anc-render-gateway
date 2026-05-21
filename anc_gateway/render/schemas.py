from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from anc_gateway.core.schemas import PromptSourceMap


class RenderJobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RenderJobCreateRequest(BaseModel):
    condition_hash: str
    compiled_prompt: str
    source_map: PromptSourceMap
    vendor: str = "mock"
    model: str = "mock-video-v1"
    visual_anchor_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RenderJobResponse(BaseModel):
    job_id: str
    status: RenderJobStatus
    condition_hash: str
    render_hash: str
    vendor: str
    model: str
    video_uri: str | None
    error_message: str | None
    created_at: str | None
    updated_at: str | None


class RenderJobFailRequest(BaseModel):
    error_message: str | None = None
