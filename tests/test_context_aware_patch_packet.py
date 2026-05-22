"""Tests for context-aware patch packet generation."""

from __future__ import annotations

from anc_gateway.core.schemas import FailureCacheRecord
from anc_gateway.recovery.patch_packet import build_patch_packet


def _make_record(
    signature: str,
    bad_prompt_fragment: str,
    category: str = "topology_dof_violation",
) -> FailureCacheRecord:
    return FailureCacheRecord(
        category=category,
        signature=signature,
        raw_signature=signature,
        recovery_policy="LEVEL_2_NEGATIVE_MITIGATION",
        bad_prompt_fragment_ref="frag_001",
        bad_prompt_fragment=bad_prompt_fragment,
        suggested_positive_lock="",
        packet_condition_hash="test_hash",
    )


def test_sliding_window_patch_contains_rail() -> None:
    record = _make_record("object_rotation_error", "她轻轻推开了推拉窗。")
    patch = build_patch_packet(record)
    assert "轨道" in patch.patch_prompt
    assert "窗扇" in patch.patch_prompt
    assert "水平滑动" in patch.patch_prompt
    assert "窗扇" not in patch.positive_lock or "轨道" in patch.positive_lock


def test_valve_patch_contains_center_axis() -> None:
    record = _make_record("object_rotation_error", "她顺时针旋转阀门。")
    patch = build_patch_packet(record)
    assert "中心轴" in patch.patch_prompt
    assert "阀门" in patch.patch_prompt
    assert "窗扇" not in patch.patch_prompt
    assert "窗扇" not in patch.positive_lock


def test_hinged_door_patch_contains_hinge() -> None:
    record = _make_record("object_rotation_error", "她握住门把手，将门板向外推开。")
    patch = build_patch_packet(record)
    assert "铰链" in patch.patch_prompt
    assert "门板" in patch.patch_prompt
    assert "窗扇" not in patch.patch_prompt


def test_drawer_patch_contains_slide_rail() -> None:
    record = _make_record("object_rotation_error", "她将抽屉从滑轨中拉出。")
    patch = build_patch_packet(record)
    assert "滑轨" in patch.patch_prompt
    assert "抽屉" in patch.patch_prompt
    assert "窗扇" not in patch.patch_prompt


def test_button_panel_patch_contains_finger() -> None:
    record = _make_record("hand_panel_misalignment", "她的手指悬停在按钮面板上方。")
    patch = build_patch_packet(record)
    assert "手指" in patch.patch_prompt
    assert "按钮" in patch.patch_prompt


def test_extra_limb_patch_contains_body_constraint() -> None:
    record = _make_record(
        "extra_limb_generated",
        "她用三只手同时抓住了绳子。",
        category="identity_drift",
    )
    patch = build_patch_packet(record)
    assert "肢体" in patch.patch_prompt or "手臂" in patch.patch_prompt
    assert "额外" in patch.patch_prompt or "不生成" in patch.patch_prompt
    assert "五根手指" in patch.positive_lock or "手指" in patch.positive_lock


def test_visual_anchor_patch_contains_continuity() -> None:
    record = _make_record(
        "visual_anchor_ignored",
        "红色的裙子被生成成了蓝色。",
        category="spatial_drift",
    )
    patch = build_patch_packet(record)
    assert "参考" in patch.patch_prompt or "一致" in patch.patch_prompt
    assert "场景跳变" in patch.positive_lock or "风格漂移" in patch.positive_lock


def test_patch_packet_contains_patch_context() -> None:
    record = _make_record("object_rotation_error", "她轻轻推开了推拉窗。")
    patch = build_patch_packet(record)
    assert patch.patch_context
    assert patch.patch_context["object_type"] == "sliding_window"
    assert patch.patch_context["motion_model"] == "horizontal_track_slide"
    assert patch.patch_context["confidence"] == 0.9


def test_different_objects_different_patches() -> None:
    window = _make_record("object_rotation_error", "她轻轻推开了推拉窗。")
    valve = _make_record("object_rotation_error", "她顺时针旋转阀门。")
    door = _make_record("object_rotation_error", "她握住门把手，将门板推开。")
    drawer = _make_record("object_rotation_error", "她将抽屉从滑轨中拉出。")

    p_window = build_patch_packet(window)
    p_valve = build_patch_packet(valve)
    p_door = build_patch_packet(door)
    p_drawer = build_patch_packet(drawer)

    prompts = {p_window.patch_prompt, p_valve.patch_prompt, p_door.patch_prompt, p_drawer.patch_prompt}
    assert len(prompts) == 4, f"Expected 4 unique prompts, got {len(prompts)}"


def test_generic_fallback_preserves_suggested_lock() -> None:
    record = FailureCacheRecord(
        category="unknown_failure",
        signature="unknown_failure",
        raw_signature="unknown_failure",
        recovery_policy="LEVEL_2_NEGATIVE_MITIGATION",
        bad_prompt_fragment_ref="frag_001",
        bad_prompt_fragment="一些随机文本。",
        suggested_positive_lock="保持稳定。",
        packet_condition_hash="test_hash",
    )
    patch = build_patch_packet(record)
    assert "保持稳定" in patch.patch_prompt
