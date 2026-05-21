from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from anc_gateway.core.schemas import RenderContract, StateT


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def stable_json_dumps(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_condition_hash(
    *,
    compiled_prompt: str,
    state: StateT,
    render_contract: RenderContract,
) -> str:
    payload = {
        "compiled_prompt": compiled_prompt,
        "state_id": state.id,
        "shot_id": render_contract.shot_id,
        "ruleset_fingerprint": render_contract.ruleset_fingerprint,
        "compiler_version": render_contract.compiler_version,
    }
    return sha256_text(stable_json_dumps(payload))
