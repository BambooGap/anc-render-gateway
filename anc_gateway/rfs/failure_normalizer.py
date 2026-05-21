from __future__ import annotations

from anc_gateway.core.schemas import CompiledRenderPacket, FailureCacheRecord, RFSAuditResult
from anc_gateway.rfs.failure_taxonomy import normalize_failure_signature
from anc_gateway.rfs.source_map_attribution import attribute_failure_fragment


_POSITIVE_LOCKS_BY_SIGNATURE = {
    "object_rotation_error": "窗扇始终保持垂直平面姿态，只沿上下轨道做水平滑动。",
    "hand_panel_misalignment": "手掌持续贴合目标物体表面，接触边界清晰可见。",
}


def normalize_rfs_failure(
    audit: RFSAuditResult, packet: CompiledRenderPacket
) -> FailureCacheRecord:
    normalized = normalize_failure_signature(audit.raw_signature)
    fragment = attribute_failure_fragment(packet, audit.bad_prompt_fragment_ref)
    suggested_lock = _POSITIVE_LOCKS_BY_SIGNATURE.get(
        normalized.signature,
        "保持目标对象的空间关系和运动约束稳定，不引入新的动作自由度。",
    )
    return FailureCacheRecord(
        category=normalized.category,
        signature=normalized.signature,
        raw_signature=audit.raw_signature,
        recovery_policy="LEVEL_2_NEGATIVE_MITIGATION",
        bad_prompt_fragment_ref=fragment.fragment_ref,
        bad_prompt_fragment=fragment.original_text,
        suggested_positive_lock=suggested_lock,
        packet_condition_hash=packet.condition_hash,
    )
