from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT


def test_positive_lock_rewriter_removes_negative_traps() -> None:
    packet = compile_render_packet(
        StateT(id="state_001", shot_id="shot_001"),
        RenderContract(shot_id="shot_001"),
        "不要让受伤的左臂恢复功能，不要穿模。",
    )

    assert "不要" not in packet.compiled_prompt
    assert "不能" not in packet.compiled_prompt
    assert "避免" not in packet.compiled_prompt
    assert "左臂持续保持无力下垂" in packet.compiled_prompt
    assert "清晰可见的接触边界" in packet.compiled_prompt

    rules = [
        rule
        for fragment in packet.source_map.fragments.values()
        for rule in fragment.rules_applied
    ]
    assert "ANC-LINT-005" in rules
