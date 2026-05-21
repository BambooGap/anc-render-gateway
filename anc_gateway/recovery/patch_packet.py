from __future__ import annotations

from anc_gateway.core.schemas import FailureCacheRecord, PatchPacket


def build_patch_packet(record: FailureCacheRecord) -> PatchPacket:
    if record.signature == "object_rotation_error":
        patch_prompt = (
            "只修正目标物体的运动拓扑。窗扇保持垂直平面姿态，"
            "只沿上下轨道水平滑动。人物、背景、光线和镜头构图保持稳定。"
        )
        target_regions = ["object_motion", "contact_surface"]
    else:
        patch_prompt = (
            "只修正失败片段对应的物理约束。"
            f"{record.suggested_positive_lock}人物、背景、光线和镜头构图保持稳定。"
        )
        target_regions = ["object_motion", "contact_surface"]

    return PatchPacket(
        recovery_policy=record.recovery_policy,
        target_fragment_ref=record.bad_prompt_fragment_ref,
        positive_lock=record.suggested_positive_lock,
        patch_prompt=patch_prompt,
        locked_regions=["actor_identity", "background", "lighting", "camera_frame"],
        target_regions=target_regions,
    )
