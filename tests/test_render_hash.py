from anc_gateway.render.hash import compute_render_hash


def test_render_hash_is_stable_for_same_inputs() -> None:
    first = compute_render_hash(
        condition_hash="condition_001",
        vendor="mock",
        model="mock-video-v1",
        visual_anchor_uri="mock://anchors/window.png",
        metadata={"quality": "draft", "seed": 1},
    )
    second = compute_render_hash(
        condition_hash="condition_001",
        vendor="mock",
        model="mock-video-v1",
        visual_anchor_uri="mock://anchors/window.png",
        metadata={"seed": 1, "quality": "draft"},
    )

    assert first == second


def test_render_hash_changes_when_visual_anchor_changes() -> None:
    first = compute_render_hash(
        condition_hash="condition_001",
        vendor="mock",
        model="mock-video-v1",
        visual_anchor_uri="mock://anchors/window-a.png",
        metadata={"seed": 1},
    )
    second = compute_render_hash(
        condition_hash="condition_001",
        vendor="mock",
        model="mock-video-v1",
        visual_anchor_uri="mock://anchors/window-b.png",
        metadata={"seed": 1},
    )

    assert first != second
