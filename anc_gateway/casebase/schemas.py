"""Schemas for Casebase search, stats, and recommendations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CasebaseSearchResult(BaseModel):
    case_id: str
    case_title: str
    attempt_id: str
    attempt_index: int
    failure_signature: str | None = None
    failure_category: str | None = None
    bad_prompt_fragment: str | None = None
    recovery_policy: str | None = None
    patch_prompt: str | None = None
    positive_lock: str | None = None
    result_video_uri: str | None = None
    created_at: str | None = None


class FailureSignatureStat(BaseModel):
    failure_signature: str
    count: int
    latest_case_id: str | None = None
    latest_case_title: str | None = None
    latest_patch_prompt: str | None = None


class PatchRecordItem(BaseModel):
    patch_record_id: str
    failure_record_id: str | None = None
    failure_signature: str | None = None
    recovery_policy: str | None = None
    patch_prompt: str | None = None
    positive_lock: str | None = None
    target_fragment_ref: str | None = None
    case_id: str | None = None
    case_title: str | None = None
    attempt_id: str | None = None
    created_at: str | None = None


class RecommendRequest(BaseModel):
    failure_signature: str
    bad_prompt_fragment: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class RecommendedPatch(BaseModel):
    patch_record_id: str | None = None
    failure_record_id: str | None = None
    failure_signature: str
    recovery_policy: str | None = None
    patch_prompt: str | None = None
    positive_lock: str | None = None
    target_fragment_ref: str | None = None
    case_id: str | None = None
    case_title: str | None = None
    confidence: float
    matched_by: str


class RecommendResponse(BaseModel):
    recommended_patches: list[RecommendedPatch]
    total_candidates: int
