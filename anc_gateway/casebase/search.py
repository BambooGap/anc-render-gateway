"""Casebase search functionality."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from anc_gateway.casebase.schemas import CasebaseSearchResult
from anc_gateway.storage.models import (
    AttemptModel,
    CaseModel,
    FailureRecordModel,
    ManualAuditModel,
    PatchRecordModel,
)


def search_casebase(
    session: Session,
    *,
    failure_signature: str | None = None,
    failure_category: str | None = None,
    raw_failure_type: str | None = None,
    q: str | None = None,
    limit: int = 20,
) -> list[CasebaseSearchResult]:
    """Search casebase by failure signature, category, or text query."""
    bounded_limit = max(1, min(limit, 100))

    # Build base query joining attempts with cases and failures
    query = (
        select(
            CaseModel.id.label("case_id"),
            CaseModel.title.label("case_title"),
            AttemptModel.id.label("attempt_id"),
            AttemptModel.attempt_index,
            AttemptModel.failure_record_id,
            AttemptModel.patch_prompt,
            AttemptModel.result_video_uri,
            AttemptModel.created_at,
        )
        .join(AttemptModel, AttemptModel.case_id == CaseModel.id)
        .where(AttemptModel.failure_record_id.isnot(None))
    )

    # Apply failure signature filter
    if failure_signature:
        query = query.join(
            FailureRecordModel,
            FailureRecordModel.id == AttemptModel.failure_record_id,
        ).where(FailureRecordModel.failure_signature == failure_signature)

    # Apply failure category filter
    if failure_category:
        if not failure_signature:
            query = query.join(
                FailureRecordModel,
                FailureRecordModel.id == AttemptModel.failure_record_id,
            )
        query = query.where(FailureRecordModel.failure_category == failure_category)

    # Apply raw failure type filter
    if raw_failure_type:
        query = query.join(
            ManualAuditModel,
            ManualAuditModel.manual_job_id == AttemptModel.manual_job_id,
        ).where(ManualAuditModel.raw_failure_type == raw_failure_type)

    # Apply text search
    if q:
        search_pattern = f"%{q}%"
        text_conditions = [
            CaseModel.title.ilike(search_pattern),
            CaseModel.raw_prompt.ilike(search_pattern),
            AttemptModel.raw_prompt.ilike(search_pattern),
        ]
        if not failure_signature and not failure_category:
            query = query.join(
                FailureRecordModel,
                FailureRecordModel.id == AttemptModel.failure_record_id,
            )
        text_conditions.extend([
            FailureRecordModel.bad_prompt_fragment.ilike(search_pattern),
            FailureRecordModel.failure_signature.ilike(search_pattern),
        ])
        query = query.where(or_(*text_conditions))

    # Order by created_at desc and limit
    query = query.order_by(AttemptModel.created_at.desc()).limit(bounded_limit)

    rows = session.execute(query).all()

    results: list[CasebaseSearchResult] = []
    for row in rows:
        # Get failure record details if available
        failure_signature_val = None
        failure_category_val = None
        bad_prompt_fragment = None
        recovery_policy = None
        positive_lock = None

        if row.failure_record_id:
            failure = session.get(FailureRecordModel, row.failure_record_id)
            if failure:
                failure_signature_val = failure.failure_signature
                failure_category_val = failure.failure_category
                bad_prompt_fragment = failure.bad_prompt_fragment
                recovery_policy = failure.recovery_policy

        # Get patch record if available
        patch_record = session.scalar(
            select(PatchRecordModel).where(
                PatchRecordModel.failure_record_id == row.failure_record_id
            )
        )
        if patch_record:
            positive_lock = patch_record.positive_lock

        results.append(
            CasebaseSearchResult(
                case_id=row.case_id,
                case_title=row.case_title,
                attempt_id=row.attempt_id,
                attempt_index=row.attempt_index,
                failure_signature=failure_signature_val,
                failure_category=failure_category_val,
                bad_prompt_fragment=bad_prompt_fragment,
                recovery_policy=recovery_policy,
                patch_prompt=row.patch_prompt,
                positive_lock=positive_lock,
                result_video_uri=row.result_video_uri,
                created_at=row.created_at.isoformat() if row.created_at else None,
            )
        )

    return results
