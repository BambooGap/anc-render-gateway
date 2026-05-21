from anc_gateway.manual.instructions import build_manual_instructions
from anc_gateway.manual.schemas import ManualVendorPlatform


def test_jimeng_web_instructions_include_safety_boundaries() -> None:
    instructions = build_manual_instructions(
        ManualVendorPlatform.JIMENG_WEB,
        "窗扇沿上下轨道水平滑动",
        "file:///tmp/anchor.png",
    )

    assert "即梦" in instructions
    assert "窗扇沿上下轨道水平滑动" in instructions
    assert "不要模拟登录" in instructions
    assert "不要抓取 cookie" in instructions


def test_gemini_flow_instructions_mention_gemini_or_flow() -> None:
    instructions = build_manual_instructions(
        ManualVendorPlatform.GEMINI_FLOW,
        "窗扇沿上下轨道水平滑动",
        None,
    )

    assert "Gemini" in instructions or "Flow" in instructions
    assert "窗扇沿上下轨道水平滑动" in instructions


def test_generic_web_instructions_include_prompt() -> None:
    instructions = build_manual_instructions(
        ManualVendorPlatform.GENERIC_WEB,
        "窗扇沿上下轨道水平滑动",
        None,
    )

    assert "目标视频生成网页" in instructions
    assert "窗扇沿上下轨道水平滑动" in instructions
