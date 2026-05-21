from anc_gateway.vendors.jitter import apply_soft_constraint_jitter


def test_soft_constraint_jitter_preserves_hard_topology_terms() -> None:
    prompt = (
        "窗扇始终保持垂直平面姿态，只沿上下轨道水平滑动。"
        "圆形金属阀门围绕中心轴旋转。漂浮尘埃缓慢穿过冷白光束。"
    )

    jittered = apply_soft_constraint_jitter(prompt, attempt=2)

    assert "上下轨道" in jittered
    assert "水平滑动" in jittered
    assert "中心轴" in jittered
    assert "旋转" in jittered
    assert jittered != prompt


def test_soft_constraint_jitter_attempt_zero_is_noop() -> None:
    prompt = "窗扇沿上下轨道水平滑动。"

    assert apply_soft_constraint_jitter(prompt, attempt=0) == prompt
