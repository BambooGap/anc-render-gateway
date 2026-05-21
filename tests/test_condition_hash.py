from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT


def test_condition_hash_includes_ruleset() -> None:
    state = StateT(id="state_001", shot_id="shot_001")
    prompt = "她轻轻推开了推拉窗，风吹进房间。"

    packet_rc1 = compile_render_packet(
        state,
        RenderContract(shot_id="shot_001", ruleset_fingerprint="rc1"),
        prompt,
    )
    packet_rc2 = compile_render_packet(
        state,
        RenderContract(shot_id="shot_001", ruleset_fingerprint="rc2"),
        prompt,
    )

    assert packet_rc1.condition_hash != packet_rc2.condition_hash
