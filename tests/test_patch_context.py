"""Tests for infer_object_context."""

from __future__ import annotations

from anc_gateway.recovery.context import infer_object_context


def test_sliding_window_recognized() -> None:
    ctx = infer_object_context(
        failure_signature="object_rotation_error",
        bad_prompt_fragment="她轻轻推开了推拉窗，风吹进房间。",
    )
    assert ctx.object_type == "sliding_window"
    assert ctx.motion_model == "horizontal_track_slide"
    assert ctx.confidence == 0.9


def test_valve_recognized() -> None:
    ctx = infer_object_context(
        failure_signature="object_rotation_error",
        bad_prompt_fragment="她顺时针旋转阀门，水流逐渐变小。",
    )
    assert ctx.object_type == "valve"
    assert ctx.motion_model == "center_axis_rotation"


def test_hinged_door_recognized() -> None:
    ctx = infer_object_context(
        failure_signature="object_rotation_error",
        bad_prompt_fragment="她握住门把手，将门板向外推开。",
    )
    assert ctx.object_type == "hinged_door"
    assert ctx.motion_model == "hinge_rotation"


def test_drawer_recognized() -> None:
    ctx = infer_object_context(
        failure_signature="object_rotation_error",
        bad_prompt_fragment="她握住抽屉把手，将抽屉从滑轨中拉出。",
    )
    assert ctx.object_type == "drawer"
    assert ctx.motion_model == "drawer_slide"


def test_button_panel_recognized() -> None:
    ctx = infer_object_context(
        failure_signature="hand_panel_misalignment",
        bad_prompt_fragment="她的手指悬停在按钮面板上方。",
    )
    assert ctx.object_type == "button_panel"
    assert ctx.motion_model == "surface_contact"


def test_human_body_recognized_by_signature() -> None:
    ctx = infer_object_context(
        failure_signature="extra_limb_generated",
        bad_prompt_fragment="她用三只手同时抓住了绳子。",
    )
    assert ctx.object_type == "human_body"
    assert ctx.motion_model == "body_structure_lock"


def test_human_body_recognized_by_keywords() -> None:
    ctx = infer_object_context(
        failure_signature="some_other_sig",
        bad_prompt_fragment="她的背后多出了一条手臂在挥舞。",
    )
    assert ctx.object_type == "human_body"
    assert ctx.motion_model == "body_structure_lock"


def test_visual_anchor_recognized_by_signature() -> None:
    ctx = infer_object_context(
        failure_signature="visual_anchor_ignored",
        bad_prompt_fragment="红色的裙子被生成成了蓝色。",
    )
    assert ctx.object_type == "visual_anchor"
    assert ctx.motion_model == "scene_continuity_lock"


def test_visual_anchor_recognized_by_keywords() -> None:
    ctx = infer_object_context(
        failure_signature="some_sig",
        bad_prompt_fragment="参考图场景跳变，风格不一致。",
    )
    assert ctx.object_type == "visual_anchor"
    assert ctx.motion_model == "scene_continuity_lock"


def test_generic_object_fallback() -> None:
    ctx = infer_object_context(
        failure_signature="unknown_failure",
        bad_prompt_fragment="一些随机文本。",
    )
    assert ctx.object_type == "generic_object"
    assert ctx.motion_model == "unknown"
    assert ctx.confidence == 0.3


def test_notes_used_for_context() -> None:
    ctx = infer_object_context(
        failure_signature="object_rotation_error",
        notes="阀门圆盘向外翻转了。",
    )
    assert ctx.object_type == "valve"


def test_compiled_prompt_used_for_context() -> None:
    ctx = infer_object_context(
        failure_signature="object_rotation_error",
        compiled_prompt="推拉窗沿着上下轨道水平滑动。",
    )
    assert ctx.object_type == "sliding_window"
