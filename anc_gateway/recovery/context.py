"""Object context inference for context-aware patch generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ObjectContext:
    object_type: str
    motion_model: str | None
    confidence: float
    evidence: str | None


# ── Keyword rules ──────────────────────────────────────────────────────

_SLIDING_WINDOW_KEYWORDS = ("推拉窗", "窗扇", "上下轨道", "水平滑动", "滑动窗", "推拉门")
_VALVE_KEYWORDS = ("阀门", "圆形阀门", "中心轴", "顺时针", "逆时针", "水阀", "气阀")
_HINGED_DOOR_KEYWORDS = ("门把手", "铰链", "门板", "门框", "向外开", "向内开")
_DRAWER_KEYWORDS = ("抽屉", "滑轨", "拉出", "推入", "抽拉")
_BUTTON_PANEL_KEYWORDS = ("按钮", "面板", "控制台", "按下", "触摸屏", "开关")
_HUMAN_BODY_KEYWORDS = ("多出一只手", "多出手臂", "多出手指", "额外肢体", "多余肢体", "多指", "三只手", "多出了", "多了")
_VISUAL_ANCHOR_KEYWORDS = ("参考图", "场景跳变", "风格漂移", "背景变化", "风格不一致", "场景布局")


def infer_object_context(
    failure_signature: str,
    bad_prompt_fragment: str | None = None,
    notes: str | None = None,
    compiled_prompt: str | None = None,
) -> ObjectContext:
    """Infer object type and motion model from failure context."""
    text = " ".join(filter(None, [bad_prompt_fragment, notes, compiled_prompt]))

    # Rule 6: extra_limb_generated -> human_body
    if failure_signature == "extra_limb_generated" or _contains_any(text, _HUMAN_BODY_KEYWORDS):
        return ObjectContext(
            object_type="human_body",
            motion_model="body_structure_lock",
            confidence=0.9,
            evidence="extra_limb_detected",
        )

    # Rule 7: visual_anchor_ignored -> visual_anchor
    if failure_signature == "visual_anchor_ignored" or _contains_any(text, _VISUAL_ANCHOR_KEYWORDS):
        return ObjectContext(
            object_type="visual_anchor",
            motion_model="scene_continuity_lock",
            confidence=0.9,
            evidence="visual_anchor_issue",
        )

    # Rule 1: sliding_window
    if _contains_any(text, _SLIDING_WINDOW_KEYWORDS):
        return ObjectContext(
            object_type="sliding_window",
            motion_model="horizontal_track_slide",
            confidence=0.9,
            evidence="sliding_window_keywords",
        )

    # Rule 2: valve
    if _contains_any(text, _VALVE_KEYWORDS):
        return ObjectContext(
            object_type="valve",
            motion_model="center_axis_rotation",
            confidence=0.9,
            evidence="valve_keywords",
        )

    # Rule 3: hinged_door
    if _contains_any(text, _HINGED_DOOR_KEYWORDS):
        return ObjectContext(
            object_type="hinged_door",
            motion_model="hinge_rotation",
            confidence=0.9,
            evidence="hinged_door_keywords",
        )

    # Rule 4: drawer
    if _contains_any(text, _DRAWER_KEYWORDS):
        return ObjectContext(
            object_type="drawer",
            motion_model="drawer_slide",
            confidence=0.9,
            evidence="drawer_keywords",
        )

    # Rule 5: button_panel
    if _contains_any(text, _BUTTON_PANEL_KEYWORDS):
        return ObjectContext(
            object_type="button_panel",
            motion_model="surface_contact",
            confidence=0.9,
            evidence="button_panel_keywords",
        )

    # Rule 8: fallback
    return ObjectContext(
        object_type="generic_object",
        motion_model="unknown",
        confidence=0.3,
        evidence="no_matching_keywords",
    )


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in text for kw in keywords)
