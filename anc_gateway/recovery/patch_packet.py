"""Context-aware patch packet builder."""

from __future__ import annotations

from anc_gateway.core.schemas import FailureCacheRecord, PatchPacket
from anc_gateway.recovery.context import ObjectContext, infer_object_context


def build_patch_packet(record: FailureCacheRecord) -> PatchPacket:
    """Build a patch packet with context-aware templates."""
    ctx = infer_object_context(
        failure_signature=record.signature,
        bad_prompt_fragment=record.bad_prompt_fragment,
    )
    patch_prompt, positive_lock = _select_template(record.signature, ctx, record.suggested_positive_lock)

    return PatchPacket(
        recovery_policy=record.recovery_policy,
        target_fragment_ref=record.bad_prompt_fragment_ref,
        positive_lock=positive_lock,
        patch_prompt=patch_prompt,
        locked_regions=["actor_identity", "background", "lighting", "camera_frame"],
        target_regions=["object_motion", "contact_surface"],
        patch_context={
            "object_type": ctx.object_type,
            "motion_model": ctx.motion_model,
            "confidence": ctx.confidence,
            "evidence": ctx.evidence,
        },
    )


def _select_template(
    failure_signature: str, ctx: ObjectContext, suggested_positive_lock: str = ""
) -> tuple[str, str]:
    """Select patch_prompt and positive_lock based on signature + context."""

    # ── object_rotation_error ──────────────────────────────────────────
    if failure_signature == "object_rotation_error":
        if ctx.object_type == "sliding_window":
            return (
                "只修正目标物体的运动拓扑。窗扇保持垂直平面姿态，只沿上下轨道水平滑动。"
                "人物、背景、光线和镜头构图保持稳定。",
                "窗扇始终嵌在上下轨道之间，运动方向被限制为水平滑动，"
                "不发生向外翻转或绕边缘旋转。",
            )
        if ctx.object_type == "valve":
            return (
                "只修正目标物体的运动拓扑。圆形阀门保持安装在管道平面上，"
                "只围绕自身中心轴旋转。人物、背景、光线和镜头构图保持稳定。",
                "阀门圆盘位置固定在管道接口处，双手握住阀门边缘，"
                "阀门只做顺时针或逆时针中心轴旋转，不像门板一样向外打开。",
            )
        if ctx.object_type == "hinged_door":
            return (
                "只修正目标物体的运动拓扑。门板围绕铰链轴缓慢旋转打开，"
                "门板边缘保持连接在铰链侧。人物、背景、光线和镜头构图保持稳定。",
                "门的运动被限制为绕垂直铰链轴旋转，"
                "不发生横向滑动或脱离门框。",
            )
        if ctx.object_type == "drawer":
            return (
                "只修正目标物体的运动拓扑。抽屉沿水平滑轨向外直线滑出，"
                "抽屉本体保持水平姿态。人物、背景、光线和镜头构图保持稳定。",
                "抽屉只能沿滑轨前后平移，不向上翻转，不绕边缘旋转。",
            )
        # fallback for object_rotation_error
        return (
            "只修正目标物体的运动拓扑。物体保持原始安装姿态，"
            "只沿允许的自由度方向运动。人物、背景、光线和镜头构图保持稳定。",
            "物体运动被限制在允许的自由度范围内，不发生意外翻转或脱离。",
        )

    # ── hand_panel_misalignment ────────────────────────────────────────
    if failure_signature == "hand_panel_misalignment":
        if ctx.object_type == "button_panel":
            return (
                "只修正失败片段对应的物理约束。手指指腹持续贴合按钮表面，"
                "按钮受力点与手指接触点重合。人物、背景、光线和镜头构图保持稳定。",
                "手指、按钮和面板保持清晰可见的接触边界，"
                "按钮按下动作由手指接触触发。",
            )
        return (
            "只修正失败片段对应的物理约束。手掌持续贴合目标物体表面，"
            "接触边界清晰可见。人物、背景、光线和镜头构图保持稳定。",
            "手掌持续贴合目标物体表面，接触边界清晰可见。",
        )

    # ── extra_limb_generated ───────────────────────────────────────────
    if failure_signature == "extra_limb_generated":
        return (
            "只修正失败片段对应的身体结构约束。角色始终保持固定肢体数量，"
            "不生成额外手臂、手掌、手指或重复肢体。"
            "人物、背景、光线和镜头构图保持稳定。",
            "身体轮廓保持稳定，每只手保持五根手指，左右手数量固定，"
            "画面中不新增额外肢体。",
        )

    # ── visual_anchor_ignored ──────────────────────────────────────────
    if failure_signature == "visual_anchor_ignored":
        return (
            "只修正失败片段对应的视觉一致性约束。场景布局、角色服装、"
            "主体位置和镜头方向保持与参考画面一致。"
            "人物、背景、光线和镜头构图保持稳定。",
            "视觉锚点中的人物身份、服装、空间布局、背景结构和光照方向持续保持，"
            "不发生场景跳变或风格漂移。",
        )

    # ── fallback ───────────────────────────────────────────────────────
    return (
        "只修正失败片段对应的物理约束。"
        f"{suggested_positive_lock}人物、背景、光线和镜头构图保持稳定。",
        suggested_positive_lock,
    )
