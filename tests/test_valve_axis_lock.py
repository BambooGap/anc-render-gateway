from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, SceneObject, StateT


def test_valve_axis_lock() -> None:
    state = StateT(
        id="state_001",
        shot_id="shot_001",
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
        RenderContract(shot_id="shot_001"),
        "她打开阀门。",
    )

    assert "圆形金属阀门" in packet.compiled_prompt
    assert "中心轴" in packet.compiled_prompt
    assert "旋转" in packet.compiled_prompt
    assert "拉开阀门" not in packet.compiled_prompt
    assert "推开阀门" not in packet.compiled_prompt
