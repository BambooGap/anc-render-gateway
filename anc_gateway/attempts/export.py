from __future__ import annotations

from anc_gateway.storage.models import AttemptModel, CaseModel


def build_case_timeline(attempts: list[AttemptModel]) -> list[dict[str, object]]:
    return [
        {
            "type": "attempt",
            "attempt_id": attempt.id,
            "attempt_index": attempt.attempt_index,
            "status": attempt.status,
            "raw_prompt": attempt.raw_prompt,
            "condition_hash": attempt.condition_hash,
            "result_video_uri": attempt.result_video_uri,
            "failure_record_id": attempt.failure_record_id,
            "patch_record_id": attempt.patch_record_id,
            "patch_prompt": attempt.patch_prompt,
            "notes": attempt.notes,
            "created_at": attempt.created_at.isoformat() if attempt.created_at else None,
        }
        for attempt in attempts
    ]


def export_case_markdown(case: CaseModel, attempts: list[AttemptModel]) -> str:
    lines: list[str] = [
        f"# {case.title}",
        "",
        "## Base Prompt",
        "",
        case.raw_prompt,
        "",
        "## Attempts",
        "",
    ]
    for attempt in attempts:
        lines.extend(
            [
                f"### Attempt {attempt.attempt_index}",
                "",
                f"- Status: {attempt.status}",
                f"- Raw Prompt: {attempt.raw_prompt}",
            ]
        )
        if attempt.compiled_prompt:
            lines.append(f"- Compiled Prompt: {attempt.compiled_prompt}")
        if attempt.result_video_uri:
            lines.append(f"- Result Video URI: {attempt.result_video_uri}")
        if attempt.failure_record_id:
            lines.append(f"- Failure Record ID: {attempt.failure_record_id}")
        if attempt.patch_record_id:
            lines.append(f"- Patch Record ID: {attempt.patch_record_id}")
        else:
            lines.append("- Patch Record ID: None")
        if attempt.notes:
            lines.append(f"- Notes: {attempt.notes}")
        lines.append("")

    lines.extend(["## Lessons Learned", ""])
    lessons = _lesson_lines(attempts)
    lines.extend(lessons or ["- No failures or patch prompts recorded yet."])
    lines.append("")
    return "\n".join(lines)


def _lesson_lines(attempts: list[AttemptModel]) -> list[str]:
    lessons: list[str] = []
    for attempt in attempts:
        if attempt.failure_record_id:
            lessons.append(
                f"- Attempt {attempt.attempt_index}: failure_record_id={attempt.failure_record_id}"
            )
        if attempt.patch_prompt:
            lessons.append(
                f"- Attempt {attempt.attempt_index}: 修复约束：{attempt.patch_prompt}"
            )
        if "下一轮修复约束" in attempt.raw_prompt:
            lessons.append(
                f"- Attempt {attempt.attempt_index}: 下一轮 Prompt 已合并上一轮修复约束。"
            )
    return lessons
