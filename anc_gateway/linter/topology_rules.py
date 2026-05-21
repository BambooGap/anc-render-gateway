from __future__ import annotations

from anc_gateway.core.schemas import StateT
from anc_gateway.linter.rule_dsl import LintIssue, LintResult


SLIDING_WINDOW_LOCK = (
    "她右手握住窗扇右侧金属边框，窗扇始终保持垂直平面姿态，"
    "只沿上下轨道向右水平滑动，窗口左侧逐渐露出缺口"
)

VALVE_AXIS_LOCK = (
    "她右手握住圆形金属阀门外缘，阀门围绕固定中心轴顺时针旋转，"
    "手掌持续贴合阀门外缘施力"
)


def apply_topology_rules(text: str, fragment_ref: str, state: StateT) -> LintResult:
    issues: list[LintIssue] = []
    rewritten = text

    if "推拉窗" in text and any(verb in text for verb in ("推开", "打开")):
        rewritten = _replace_sliding_window_phrase(rewritten)
        issues.append(
            LintIssue(
                rule_id="ANC-LINT-001",
                message="Ambiguous motion verb for sliding window.",
                fragment_ref=fragment_ref,
                replacement_text=SLIDING_WINDOW_LOCK,
            )
        )
        issues.append(
            LintIssue(
                rule_id="ANC-LINT-002",
                message="Missing sliding-window topology constraints.",
                fragment_ref=fragment_ref,
                replacement_text=SLIDING_WINDOW_LOCK,
            )
        )

    if "推拉窗" in text and ("向外" in text or "翻开" in text):
        rewritten = rewritten.replace("向外打开", "沿上下轨道水平滑动")
        rewritten = rewritten.replace("向外翻开", "沿上下轨道水平滑动")
        issues.append(
            LintIssue(
                rule_id="ANC-LINT-004",
                message="Inconsistent DOF for sliding-window topology.",
                fragment_ref=fragment_ref,
                replacement_text=SLIDING_WINDOW_LOCK,
            )
        )

    if _has_valve_context(text, state):
        rewritten = _replace_valve_phrase(rewritten)
        issues.append(
            LintIssue(
                rule_id="ANC-LINT-002",
                message="Missing valve axis topology.",
                fragment_ref=fragment_ref,
                replacement_text=VALVE_AXIS_LOCK,
            )
        )

    return LintResult(text=rewritten, issues=issues)


def _replace_sliding_window_phrase(text: str) -> str:
    replacements = {
        "她轻轻推开了推拉窗": SLIDING_WINDOW_LOCK,
        "她推开了推拉窗": SLIDING_WINDOW_LOCK,
        "她打开了推拉窗": SLIDING_WINDOW_LOCK,
        "她轻轻推开推拉窗": SLIDING_WINDOW_LOCK,
        "推开了推拉窗": "推动推拉窗时，" + SLIDING_WINDOW_LOCK,
        "推开推拉窗": "推动推拉窗时，" + SLIDING_WINDOW_LOCK,
        "打开推拉窗": "打开推拉窗时，" + SLIDING_WINDOW_LOCK,
    }
    for source, target in replacements.items():
        if source in text:
            return text.replace(source, target)
    return f"{text}。{SLIDING_WINDOW_LOCK}"


def _has_valve_context(text: str, state: StateT) -> bool:
    if "阀门" not in text:
        return False
    if any(verb in text for verb in ("打开", "拧开", "旋转")):
        return True
    return any(obj.object_type == "valve" or obj.name == "阀门" for obj in state.objects)


def _replace_valve_phrase(text: str) -> str:
    for source in ("她打开阀门", "她打开了阀门", "打开阀门"):
        if source in text:
            return text.replace(source, VALVE_AXIS_LOCK)
    return f"{text}。{VALVE_AXIS_LOCK}"
