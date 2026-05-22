from __future__ import annotations

from typing import Any

from anc_gateway.core.schemas import PatchPacket


def merge_prompt_with_patch(base_prompt: str, patch_packet: PatchPacket | dict[str, Any]) -> str:
    return build_next_attempt_prompt(base_prompt, patch_packet)


def build_next_attempt_prompt(base_prompt: str, patch_packet: PatchPacket | dict[str, Any]) -> str:
    patch_prompt = _extract_patch_text(patch_packet)
    normalized_base = base_prompt.strip()
    if not patch_prompt:
        return normalized_base
    if patch_prompt in normalized_base:
        return normalized_base
    return f"{normalized_base}\n\n下一轮修复约束：{patch_prompt}"


def _extract_patch_text(patch_packet: PatchPacket | dict[str, Any]) -> str:
    if isinstance(patch_packet, PatchPacket):
        return patch_packet.patch_prompt or patch_packet.positive_lock
    for key in ("patch_prompt", "positive_lock", "suggested_positive_lock"):
        value = patch_packet.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""
