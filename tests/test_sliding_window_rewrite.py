from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RFSAuditResult, RenderContract, SceneObject, StateT
from anc_gateway.rfs.failure_normalizer import normalize_rfs_failure


def test_sliding_window_rewrite_and_failure_loop() -> None:
    state = StateT(
        id="state_001",
        shot_id="shot_001",
        objects=[
            SceneObject(
                id="window_01",
                name="推拉窗",
                object_type="sliding_window",
                topology={"dof": "horizontal_slide"},
            )
        ],
    )
    packet = compile_render_packet(
        state,
        RenderContract(shot_id="shot_001"),
        "她轻轻推开了推拉窗，风吹进房间。",
    )

    assert "上下轨道" in packet.compiled_prompt
    assert "水平滑动" in packet.compiled_prompt
    assert "窗扇" in packet.compiled_prompt
    assert "frag_001" in packet.source_map.fragments

    fragment = packet.source_map.fragments["frag_001"]
    assert "推开" in fragment.original_text
    assert {"ANC-LINT-001", "ANC-LINT-002"} & set(fragment.rules_applied)

    record = normalize_rfs_failure(
        RFSAuditResult(
            ok=False,
            raw_signature="window_flipping_bug",
            bad_prompt_fragment_ref="frag_001",
        ),
        packet,
    )
    assert record.signature == "object_rotation_error"
    assert record.recovery_policy == "LEVEL_2_NEGATIVE_MITIGATION"
    assert record.bad_prompt_fragment == fragment.original_text
