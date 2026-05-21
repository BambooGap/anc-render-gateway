from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, model_validator


ManualFailureType = Literal[
    "window_flipping_bug",
    "hand_not_touching_panel",
    "extra_limb_generated",
    "visual_anchor_ignored",
    "custom",
]


class ManualAuditCreateRequest(BaseModel):
    manual_job_id: str | None = None
    render_job_id: str | None = None
    condition_hash: str | None = None
    bad_prompt_fragment_ref: str
    failure_type: ManualFailureType
    notes: str | None = None
    rfs_scores: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_custom_notes(self) -> ManualAuditCreateRequest:
        if self.failure_type == "custom" and not self.notes:
            raise ValueError("notes is required when failure_type is custom")
        return self


class ManualAuditResponse(BaseModel):
    audit_id: str
    passed: bool
    failure_signature: str
    failure_category: str
    bad_prompt_fragment_ref: str
    normalized_failure_signature: str
    recovery_policy: str | None
    suggested_positive_lock: str | None
    notes: str | None
    created_at: str | None
    failure_record_id: str | None = None
