from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SceneObject(BaseModel):
    id: str
    name: str
    object_type: str
    topology: dict[str, Any] = Field(default_factory=dict)


class StateT(BaseModel):
    id: str
    shot_id: str
    objects: list[SceneObject] = Field(default_factory=list)
    actor_namespace: dict[str, Any] = Field(default_factory=dict)
    scene_context: dict[str, Any] = Field(default_factory=dict)


class RenderContract(BaseModel):
    shot_id: str
    ruleset_fingerprint: str = "rc1"
    compiler_version: str = "anc-parser-kernel/0.1.0"
    max_prompt_chars: int = 4000


class PromptFragment(BaseModel):
    fragment_ref: str
    original_text: str
    compiled_text: str
    rules_applied: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptSourceMap(BaseModel):
    fragments: dict[str, PromptFragment] = Field(default_factory=dict)


class CompiledRenderPacket(BaseModel):
    state_id: str
    shot_id: str
    compiled_prompt: str
    source_map: PromptSourceMap
    condition_hash: str
    ruleset_fingerprint: str
    compiler_version: str


class RFSAuditResult(BaseModel):
    ok: bool = False
    raw_signature: str
    bad_prompt_fragment_ref: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class FailureCacheRecord(BaseModel):
    category: str
    signature: str
    raw_signature: str
    recovery_policy: str
    bad_prompt_fragment_ref: str
    bad_prompt_fragment: str
    suggested_positive_lock: str
    packet_condition_hash: str


class PatchPacket(BaseModel):
    recovery_policy: str
    target_fragment_ref: str
    positive_lock: str
    patch_prompt: str
    locked_regions: list[str]
    target_regions: list[str]


FailureCategory = Literal[
    "topology_dof_violation",
    "contact_failure",
    "identity_drift",
    "spatial_drift",
    "actor_namespace_pollution",
    "scene_continuity_error",
    "unknown_failure",
]
