from __future__ import annotations

from anc_gateway.linter.rule_dsl import LintIssue, LintResult

NEGATIVE_TOKENS = ("不要", "不能", "避免")

POSITIVE_LOCKS = {
    "不要让受伤的左臂恢复功能": "左臂持续保持无力下垂，肩部没有主动发力，手指自然松弛",
    "不要恢复左臂功能": "左臂持续保持无力下垂，肩部没有主动发力，手指自然松弛",
    "不要穿模": "主体与物体表面保持清晰可见的接触边界，空间相互分离",
    "不要漂浮": "主体双脚持续贴合地面，身体重心由地面稳定支撑",
    "不能悬浮": "主体双脚持续贴合地面，身体重心由地面稳定支撑",
    "避免悬空": "主体双脚持续贴合地面，身体重心由地面稳定支撑",
    "不要多出手指": "每只手保持五根手指，手指数量稳定，轮廓清晰",
    "不要切换场景": "场景空间持续保持一致，背景结构和道具位置不发生切换",
    "不要出现额外人物": "画面中只保留已命名人物，背景区域不生成额外人物",
    "不能穿模": "主体与物体表面保持清晰可见的接触边界，空间相互分离",
    "避免穿模": "主体与物体表面保持清晰可见的接触边界，空间相互分离",
}


def rewrite_positive_locks(text: str, fragment_ref: str) -> LintResult:
    rewritten = text
    issues: list[LintIssue] = []
    for source, target in POSITIVE_LOCKS.items():
        if source in rewritten:
            rewritten = rewritten.replace(source, target)
            issues.append(
                LintIssue(
                    rule_id="ANC-LINT-005",
                    message="Negative prompt trap rewritten as positive lock.",
                    fragment_ref=fragment_ref,
                    replacement_text=target,
                )
            )

    for token in NEGATIVE_TOKENS:
        rewritten = rewritten.replace(token, "")

    rewritten = _clean_punctuation(rewritten)
    return LintResult(text=rewritten, issues=issues)


def _clean_punctuation(text: str) -> str:
    text = text.replace("，，", "，").replace("。。", "。")
    text = text.replace("，。", "。").replace("。,", "。")
    return text.strip("， ")
