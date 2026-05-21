from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VisualConditionEnvelope(BaseModel):
    mode: str
    primary_anchor_uri: str | None = None
    primary_anchor_role: str | None = None
    optional_anchor_uris: list[str] = Field(default_factory=list)
    mask_uri: str | None = None
    compiled_prompt: str
    negative_guardrails: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
