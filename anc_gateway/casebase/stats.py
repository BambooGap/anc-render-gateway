"""Casebase failure signature statistics."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from anc_gateway.casebase.schemas import FailureSignatureStat
from anc_gateway.storage.models import (
    AttemptModel,
    CaseModel,
    FailureRecordModel,
    PatchRecordModel,
)


def get_failure_signature_stats(session: Session) -> list[FailureSignatureStat]:
    """Get failure signature statistics ordered by count descending."""
    # Get failure signature counts
    stats_query = (
        select(
            FailureRecordModel.failure_signature,
            func.count(FailureRecordModel.id).label("count"),
        )
        .group_by(FailureRecordModel.failure_signature)
        .order_by(func.count(FailureRecordModel.id).desc())
    )

    rows = session.execute(stats_query).all()

    results: list[FailureSignatureStat] = []
    for row in rows:
        # Get latest case with this failure signature
        latest_case_query = (
            select(
                CaseModel.id,
                CaseModel.title,
            )
            .join(AttemptModel, AttemptModel.case_id == CaseModel.id)
            .join(
                FailureRecordModel,
                FailureRecordModel.id == AttemptModel.failure_record_id,
            )
            .where(FailureRecordModel.failure_signature == row.failure_signature)
            .order_by(AttemptModel.created_at.desc())
            .limit(1)
        )

        latest_case = session.execute(latest_case_query).first()

        # Get latest patch prompt for this failure signature
        latest_patch_query = (
            select(PatchRecordModel.patch_packet_json)
            .join(
                FailureRecordModel,
                FailureRecordModel.id == PatchRecordModel.failure_record_id,
            )
            .where(FailureRecordModel.failure_signature == row.failure_signature)
            .order_by(PatchRecordModel.created_at.desc())
            .limit(1)
        )

        latest_patch_json = session.scalar(latest_patch_query)
        latest_patch_prompt = None
        if latest_patch_json:
            import json

            try:
                patch_data = json.loads(latest_patch_json)
                latest_patch_prompt = patch_data.get("patch_prompt")
            except (json.JSONDecodeError, AttributeError):
                pass

        results.append(
            FailureSignatureStat(
                failure_signature=row.failure_signature,
                count=row.count,
                latest_case_id=latest_case[0] if latest_case else None,
                latest_case_title=latest_case[1] if latest_case else None,
                latest_patch_prompt=latest_patch_prompt,
            )
        )

    return results
