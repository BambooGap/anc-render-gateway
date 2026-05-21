from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from anc_gateway.core.schemas import (
    CompiledRenderPacket,
    FailureCacheRecord,
    PatchPacket,
    PromptSourceMap,
)


def model_to_json(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


def packet_to_json(packet: CompiledRenderPacket) -> dict[str, Any]:
    return model_to_json(packet)


def source_map_to_json(source_map: PromptSourceMap) -> dict[str, Any]:
    return model_to_json(source_map)


def failure_record_to_json(record: FailureCacheRecord) -> dict[str, Any]:
    return model_to_json(record)


def patch_packet_to_json(patch_packet: PatchPacket) -> dict[str, Any]:
    return model_to_json(patch_packet)


def dumps_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
