from anc_gateway.vendors.visual_envelope import VisualConditionEnvelope


def test_visual_condition_envelope_keeps_visual_inputs_together() -> None:
    envelope = VisualConditionEnvelope(
        mode="image_to_video",
        primary_anchor_uri="mock://anchors/frame.png",
        primary_anchor_role="first_frame",
        optional_anchor_uris=["mock://anchors/detail.png"],
        mask_uri=None,
        compiled_prompt="窗扇沿上下轨道水平滑动",
        negative_guardrails="不改变运动拓扑",
        metadata={"shot_id": "shot_001"},
    )

    assert envelope.primary_anchor_uri == "mock://anchors/frame.png"
    assert envelope.optional_anchor_uris == ["mock://anchors/detail.png"]
    assert "上下轨道" in envelope.compiled_prompt
    assert envelope.metadata["shot_id"] == "shot_001"
