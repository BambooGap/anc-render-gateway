from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RFSAuditResult, RenderContract, StateT
from anc_gateway.rfs.failure_normalizer import normalize_rfs_failure


def test_fragment_ids_stably_increment_and_original_text_is_preserved() -> None:
    packet = compile_render_packet(
        StateT(id="state_source_map", shot_id="shot_source_map"),
        RenderContract(shot_id="shot_source_map"),
        "她打开窗户。她把推拉窗向外打开。不要切换场景。",
    )

    assert list(packet.source_map.fragments) == ["frag_001", "frag_002", "frag_003"]
    assert packet.source_map.fragments["frag_001"].original_text == "她打开窗户"
    assert packet.source_map.fragments["frag_002"].original_text == "她把推拉窗向外打开"
    assert packet.source_map.fragments["frag_003"].original_text == "不要切换场景"
    assert packet.source_map.fragments["frag_002"].compiled_text != ""


def test_rfs_can_attribute_a_specific_fragment_in_multi_fragment_prompt() -> None:
    packet = compile_render_packet(
        StateT(id="state_multi", shot_id="shot_multi"),
        RenderContract(shot_id="shot_multi"),
        "她打开窗户。她把推拉窗向外打开。风吹进房间。",
    )

    record = normalize_rfs_failure(
        RFSAuditResult(
            ok=False,
            raw_signature="window_flipping_bug",
            bad_prompt_fragment_ref="frag_002",
        ),
        packet,
    )

    assert record.bad_prompt_fragment_ref == "frag_002"
    assert record.bad_prompt_fragment == "她把推拉窗向外打开"
