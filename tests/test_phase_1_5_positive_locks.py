from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT


def test_more_negative_constraints_are_rewritten_as_positive_locks() -> None:
    packet = compile_render_packet(
        StateT(id="state_negative", shot_id="shot_negative"),
        RenderContract(shot_id="shot_negative"),
        "不能悬浮，避免悬空，不要多出手指，不要切换场景，不要出现额外人物。",
    )

    assert "不要" not in packet.compiled_prompt
    assert "不能" not in packet.compiled_prompt
    assert "避免" not in packet.compiled_prompt
    assert "双脚持续贴合地面" in packet.compiled_prompt
    assert "每只手保持五根手指" in packet.compiled_prompt
    assert "场景空间持续保持一致" in packet.compiled_prompt
    assert "只保留已命名人物" in packet.compiled_prompt

    rules = [
        rule
        for fragment in packet.source_map.fragments.values()
        for rule in fragment.rules_applied
    ]
    assert rules.count("ANC-LINT-005") >= 1
