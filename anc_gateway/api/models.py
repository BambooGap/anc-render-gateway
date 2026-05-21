from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from anc_gateway.core.schemas import (
    CompiledRenderPacket,
    FailureCacheRecord,
    RFSAuditResult,
    RenderContract,
    StateT,
)


class CompileRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "state": {
                        "id": "state_demo_001",
                        "shot_id": "shot_001",
                        "objects": [
                            {
                                "id": "window_01",
                                "name": "推拉窗",
                                "object_type": "sliding_window",
                                "topology": {"dof": "horizontal_slide"},
                            }
                        ],
                    },
                    "render_contract": {"shot_id": "shot_001", "ruleset_fingerprint": "rc1"},
                    "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
                }
            ]
        }
    )

    state: StateT
    render_contract: RenderContract
    raw_prompt: str


class AuditRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "audit": {
                        "ok": False,
                        "raw_signature": "window_flipping_bug",
                        "bad_prompt_fragment_ref": "frag_001",
                    },
                    "packet": {"compiled_prompt": "Use a CompiledRenderPacket from /compile."},
                }
            ]
        }
    )

    audit: RFSAuditResult
    packet: CompiledRenderPacket


class RecoverRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "failure_record": {
                        "category": "topology_dof_violation",
                        "signature": "object_rotation_error",
                        "raw_signature": "window_flipping_bug",
                        "recovery_policy": "LEVEL_2_NEGATIVE_MITIGATION",
                        "bad_prompt_fragment_ref": "frag_001",
                        "bad_prompt_fragment": "她轻轻推开了推拉窗",
                        "suggested_positive_lock": "窗扇始终保持垂直平面姿态，只沿上下轨道做水平滑动。",
                        "packet_condition_hash": "example_hash",
                    }
                }
            ]
        }
    )

    failure_record: FailureCacheRecord


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str


class VersionResponse(BaseModel):
    service: str
    phase: str
    compiler_version: str
    ruleset_fingerprint: str


def error_payload(code: str, message: str, request_id: str) -> dict[str, dict[str, str]]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }


def flatten_validation_errors(errors: Sequence[Any]) -> str:
    messages: list[str] = []
    for error in errors:
        if not isinstance(error, dict):
            messages.append(str(error))
            continue
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = str(error.get("msg", "Invalid request"))
        messages.append(f"{location}: {message}" if location else message)
    return "; ".join(messages) if messages else "Invalid request"
