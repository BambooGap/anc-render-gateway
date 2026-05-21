from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, SceneObject, StateT


def test_sliding_window_outward_open_is_locked_to_horizontal_rail() -> None:
    packet = compile_render_packet(
        StateT(id="state_window", shot_id="shot_window"),
        RenderContract(shot_id="shot_window"),
        "她把推拉窗向外打开。",
    )

    assert "上下轨道" in packet.compiled_prompt
    assert "水平滑动" in packet.compiled_prompt
    assert "向外打开" not in packet.compiled_prompt
    assert "ANC-LINT-004" in packet.source_map.fragments["frag_001"].rules_applied


def test_valve_pull_open_is_locked_to_center_axis_rotation() -> None:
    state = StateT(
        id="state_valve",
        shot_id="shot_valve",
        objects=[
            SceneObject(
                id="valve_01",
                name="阀门",
                object_type="valve",
                topology={"axis": "center"},
            )
        ],
    )
    packet = compile_render_packet(
        state,
        RenderContract(shot_id="shot_valve"),
        "她拉开阀门。",
    )

    assert "圆形金属阀门" in packet.compiled_prompt
    assert "中心轴" in packet.compiled_prompt
    assert "旋转" in packet.compiled_prompt
    assert "拉开阀门" not in packet.compiled_prompt


def test_drawer_upward_flip_is_locked_to_slide_rails() -> None:
    packet = compile_render_packet(
        StateT(id="state_drawer", shot_id="shot_drawer"),
        RenderContract(shot_id="shot_drawer"),
        "她把抽屉向上翻开。",
    )

    assert "抽屉" in packet.compiled_prompt
    assert "滑轨" in packet.compiled_prompt
    assert "直线滑出" in packet.compiled_prompt
    assert "向上翻开" not in packet.compiled_prompt


def test_generic_window_open_is_flagged_as_ambiguous_topology() -> None:
    packet = compile_render_packet(
        StateT(id="state_generic_window", shot_id="shot_generic_window"),
        RenderContract(shot_id="shot_generic_window"),
        "她打开窗户。",
    )

    assert "窗户的类型" in packet.compiled_prompt
    assert "运动自由度" in packet.compiled_prompt
    assert "ANC-LINT-001" in packet.source_map.fragments["frag_001"].rules_applied


def test_panel_operation_gets_contact_boundary_lock() -> None:
    packet = compile_render_packet(
        StateT(id="state_panel", shot_id="shot_panel"),
        RenderContract(shot_id="shot_panel"),
        "他操作面板。",
    )

    assert "指尖贴合" in packet.compiled_prompt
    assert "接触边界清晰可见" in packet.compiled_prompt
    assert "面板本体保持固定" in packet.compiled_prompt


def test_door_push_open_gets_hinge_axis_lock() -> None:
    packet = compile_render_packet(
        StateT(id="state_door", shot_id="shot_door"),
        RenderContract(shot_id="shot_door"),
        "她推开门。",
    )

    assert "门把手" in packet.compiled_prompt
    assert "侧边铰链轴" in packet.compiled_prompt
    assert "旋转打开" in packet.compiled_prompt
