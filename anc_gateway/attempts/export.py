from __future__ import annotations

from sqlalchemy.orm import Session

from anc_gateway.storage.models import AttemptModel, CaseModel, FailureRecordModel, PatchRecordModel


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


def export_case_markdown(
    case: CaseModel,
    attempts: list[AttemptModel],
    session: Session | None = None,
) -> str:
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
                "",
                "#### Prompt",
                "",
                "```text",
                attempt.raw_prompt,
                "```",
                "",
            ]
        )
        if attempt.compiled_prompt:
            lines.extend(
                [
                    "#### Compiled Prompt",
                    "",
                    "```text",
                    attempt.compiled_prompt,
                    "```",
                    "",
                ]
            )
        if attempt.result_video_uri:
            lines.append(f"- Result Video URI: {attempt.result_video_uri}")
        if attempt.notes:
            lines.append(f"- Notes: {attempt.notes}")

        if attempt.failure_record_id and session is not None:
            failure_record = session.get(FailureRecordModel, attempt.failure_record_id)
            if failure_record is not None:
                lines.extend(
                    [
                        "",
                        "#### Failure Record",
                        "",
                        f"- Failure Signature: {failure_record.failure_signature}",
                        f"- Failure Category: {failure_record.failure_category}",
                        f"- Bad Prompt Fragment Ref: {failure_record.bad_prompt_fragment_ref}",
                        f"- Bad Prompt Fragment: {failure_record.bad_prompt_fragment}",
                        f"- Recovery Policy: {failure_record.recovery_policy}",
                        f"- Suggested Positive Lock: {failure_record.suggested_positive_lock}",
                    ]
                )

        if attempt.patch_record_id and session is not None:
            patch_record = session.get(PatchRecordModel, attempt.patch_record_id)
            if patch_record is not None:
                lines.extend(
                    [
                        "",
                        "#### Patch Record",
                        "",
                        f"- Recovery Policy: {patch_record.recovery_policy}",
                        f"- Target Fragment Ref: {patch_record.target_fragment_ref}",
                        f"- Positive Lock: {patch_record.positive_lock}",
                    ]
                )
        elif attempt.patch_prompt:
            lines.extend(
                [
                    "",
                    "#### Patch Prompt",
                    "",
                    "```text",
                    attempt.patch_prompt,
                    "```",
                    "",
                ]
            )

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
