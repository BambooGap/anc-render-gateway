"""Casebase patch recommendation engine."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from anc_gateway.casebase.schemas import (
    RecommendRequest,
    RecommendResponse,
    RecommendedPatch,
)
from anc_gateway.storage.models import (
    AttemptModel,
    FailureRecordModel,
    PatchRecordModel,
)

EXACT_SIGNATURE_CONFIDENCE = 0.9
CATEGORY_MATCH_CONFIDENCE = 0.7
TEXT_MATCH_CONFIDENCE = 0.5


def recommend_patches(
    session: Session,
    request: RecommendRequest,
) -> RecommendResponse:
    """Recommend patch prompts based on failure signature and optional text match."""
    bounded_limit = max(1, min(request.limit, 20))

    candidates: list[RecommendedPatch] = []

    # Strategy 1: Exact failure signature match (confidence=0.9)
    exact_matches = _find_by_failure_signature(session, request.failure_signature, bounded_limit)
    candidates.extend(exact_matches)

    # Strategy 2: Same failure category (confidence=0.7)
    if len(candidates) < bounded_limit:
        category = _get_failure_category(session, request.failure_signature)
        if category:
            category_matches = _find_by_failure_category(
                session,
                category,
                exclude_signatures={request.failure_signature},
                limit=bounded_limit - len(candidates),
            )
            candidates.extend(category_matches)

    # Strategy 3: Text similarity in bad_prompt_fragment (confidence=0.5)
    if request.bad_prompt_fragment and len(candidates) < bounded_limit:
        existing_ids = {c.failure_record_id for c in candidates if c.failure_record_id}
        text_matches = _find_by_text_similarity(
            session,
            request.bad_prompt_fragment,
            exclude_ids=existing_ids,
            limit=bounded_limit - len(candidates),
        )
        candidates.extend(text_matches)

    # Sort by confidence descending
    candidates.sort(key=lambda x: x.confidence, reverse=True)

    return RecommendResponse(
        recommended_patches=candidates[:bounded_limit],
        total_candidates=len(candidates),
    )


def _find_by_failure_signature(
    session: Session,
    failure_signature: str,
    limit: int,
) -> list[RecommendedPatch]:
    """Find patches with exact failure signature match."""
    query = (
        select(
            PatchRecordModel,
            FailureRecordModel.failure_signature,
            FailureRecordModel.failure_category,
            FailureRecordModel.bad_prompt_fragment,
            AttemptModel.case_id,
            AttemptModel.id.label("attempt_id"),
        )
        .join(
            FailureRecordModel,
            FailureRecordModel.id == PatchRecordModel.failure_record_id,
        )
        .outerjoin(
            AttemptModel,
            AttemptModel.failure_record_id == FailureRecordModel.id,
        )
        .where(FailureRecordModel.failure_signature == failure_signature)
        .order_by(PatchRecordModel.created_at.desc())
        .limit(limit)
    )

    rows = session.execute(query).all()
    return [_row_to_recommended_patch(session, row, EXACT_SIGNATURE_CONFIDENCE, "exact_signature") for row in rows]


def _find_by_failure_category(
    session: Session,
    category: str,
    *,
    exclude_signatures: set[str],
    limit: int,
) -> list[RecommendedPatch]:
    """Find patches with same failure category."""
    query = (
        select(
            PatchRecordModel,
            FailureRecordModel.failure_signature,
            FailureRecordModel.failure_category,
            FailureRecordModel.bad_prompt_fragment,
            AttemptModel.case_id,
            AttemptModel.id.label("attempt_id"),
        )
        .join(
            FailureRecordModel,
            FailureRecordModel.id == PatchRecordModel.failure_record_id,
        )
        .outerjoin(
            AttemptModel,
            AttemptModel.failure_record_id == FailureRecordModel.id,
        )
        .where(FailureRecordModel.failure_category == category)
        .where(FailureRecordModel.failure_signature.notin_(exclude_signatures))
        .order_by(PatchRecordModel.created_at.desc())
        .limit(limit)
    )

    rows = session.execute(query).all()
    return [_row_to_recommended_patch(session, row, CATEGORY_MATCH_CONFIDENCE, "same_category") for row in rows]


def _find_by_text_similarity(
    session: Session,
    text: str,
    *,
    exclude_ids: set[str],
    limit: int,
) -> list[RecommendedPatch]:
    """Find patches with similar bad_prompt_fragment text."""
    search_pattern = f"%{text}%"

    query = (
        select(
            PatchRecordModel,
            FailureRecordModel.failure_signature,
            FailureRecordModel.failure_category,
            FailureRecordModel.bad_prompt_fragment,
            AttemptModel.case_id,
            AttemptModel.id.label("attempt_id"),
        )
        .join(
            FailureRecordModel,
            FailureRecordModel.id == PatchRecordModel.failure_record_id,
        )
        .outerjoin(
            AttemptModel,
            AttemptModel.failure_record_id == FailureRecordModel.id,
        )
        .where(FailureRecordModel.bad_prompt_fragment.ilike(search_pattern))
        .order_by(PatchRecordModel.created_at.desc())
        .limit(limit)
    )

    rows = session.execute(query).all()
    results = []
    for row in rows:
        if row[0].failure_record_id not in exclude_ids:
            results.append(_row_to_recommended_patch(session, row, TEXT_MATCH_CONFIDENCE, "text_similarity"))
    return results


def _get_failure_category(session: Session, failure_signature: str) -> str | None:
    """Get failure category for a given failure signature."""
    query = (
        select(FailureRecordModel.failure_category)
        .where(FailureRecordModel.failure_signature == failure_signature)
        .limit(1)
    )
    return session.scalar(query)


def _row_to_recommended_patch(
    session: Session,
    row: Any,
    confidence: float,
    matched_by: str,
) -> RecommendedPatch:
    """Convert a query row to RecommendedPatch."""
    patch = row[0]
    case_id = row[4]
    attempt_id = row[5]

    # Get case title
    case_title = None
    if case_id:
        from anc_gateway.storage.models import CaseModel

        case = session.get(CaseModel, case_id)
        if case:
            case_title = case.title

    # Extract patch_prompt from JSON
    patch_prompt = None
    if patch.patch_packet_json:
        try:
            patch_data = json.loads(patch.patch_packet_json)
            patch_prompt = patch_data.get("patch_prompt")
        except (json.JSONDecodeError, AttributeError):
            pass

    return RecommendedPatch(
        patch_record_id=patch.id,
        failure_record_id=patch.failure_record_id,
        failure_signature=row[1],
        recovery_policy=patch.recovery_policy,
        patch_prompt=patch_prompt,
        positive_lock=patch.positive_lock,
        target_fragment_ref=patch.target_fragment_ref,
        case_id=case_id,
        case_title=case_title,
        attempt_id=attempt_id,
        confidence=confidence,
        matched_by=matched_by,
    )
