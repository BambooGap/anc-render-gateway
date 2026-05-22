"""Casebase patch recommendation engine with ranking and dedup."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from anc_gateway.casebase.schemas import (
    RecommendRequest,
    RecommendResponse,
    RecommendedPatch,
)
from anc_gateway.recovery.context import infer_object_context
from anc_gateway.storage.models import (
    AttemptModel,
    CaseModel,
    FailureRecordModel,
    PatchRecordModel,
)

EXACT_SIGNATURE_CONFIDENCE = 0.9
CATEGORY_MATCH_CONFIDENCE = 0.7
TEXT_MATCH_CONFIDENCE = 0.5

_GENERIC_PHRASES = (
    "保持目标对象的空间关系和运动约束稳定",
    "保持画面稳定",
    "保持一致",
)


def recommend_patches(
    session: Session,
    request: RecommendRequest,
) -> RecommendResponse:
    """Recommend patch prompts with ranking, dedup, and explanations."""
    bounded_limit = max(1, min(request.limit, 20))

    # Infer object context if not provided
    ctx = infer_object_context(
        failure_signature=request.failure_signature,
        bad_prompt_fragment=request.bad_prompt_fragment,
    )
    req_object_type = request.object_type or ctx.object_type
    req_motion_model = request.motion_model or ctx.motion_model

    candidates: list[RecommendedPatch] = []

    # Strategy 1: Exact failure signature match
    exact_matches = _find_by_failure_signature(session, request.failure_signature, bounded_limit * 3)
    candidates.extend(exact_matches)

    # Strategy 2: Same failure category
    category = request.failure_category or _get_failure_category(session, request.failure_signature)
    if category:
        category_matches = _find_by_failure_category(
            session,
            category,
            exclude_signatures={request.failure_signature},
            limit=bounded_limit * 2,
        )
        candidates.extend(category_matches)

    # Strategy 3: Text similarity
    if request.bad_prompt_fragment:
        existing_ids = {c.failure_record_id for c in candidates if c.failure_record_id}
        text_matches = _find_by_text_similarity(
            session,
            request.bad_prompt_fragment,
            exclude_ids=existing_ids,
            limit=bounded_limit * 2,
        )
        candidates.extend(text_matches)

    # Score and enrich each candidate
    for candidate in candidates:
        _enrich_candidate(session, candidate, request, req_object_type, req_motion_model)

    # Dedup by patch_prompt
    deduped = _dedup_candidates(candidates)

    # Sort by ranking_score descending
    deduped.sort(key=lambda x: x.ranking_score, reverse=True)

    return RecommendResponse(
        recommended_patches=deduped[:bounded_limit],
        total_candidates=len(candidates),
    )


def _enrich_candidate(
    session: Session,
    candidate: RecommendedPatch,
    request: RecommendRequest,
    req_object_type: str,
    req_motion_model: str | None,
) -> None:
    """Compute ranking_score, reason, matched_by list, and context fields."""
    score = 0.0
    reasons: list[str] = []
    matched_by: list[str] = []

    # 1. Exact failure_signature match: +0.50
    if candidate.failure_signature == request.failure_signature:
        score += 0.50
        matched_by.append("exact_signature")
        reasons.append(f"exact failure_signature {candidate.failure_signature}")

    # 2. Same failure_category: +0.25
    elif candidate.confidence == CATEGORY_MATCH_CONFIDENCE:
        score += 0.25
        matched_by.append("same_category")
        reasons.append("same failure_category")

    # 3. Text similarity: +0.10
    elif candidate.confidence == TEXT_MATCH_CONFIDENCE:
        score += 0.10
        matched_by.append("text_similarity")
        reasons.append("text similarity in bad_prompt_fragment")

    # Extract patch_context from patch_packet_json
    patch_context = _extract_patch_context(session, candidate.patch_record_id)
    candidate_object_type = patch_context.get("object_type") if patch_context else None
    candidate_motion_model = patch_context.get("motion_model") if patch_context else None
    candidate.object_type = candidate_object_type
    candidate.motion_model = candidate_motion_model

    # 4. object_type match: +0.20
    if candidate_object_type and candidate_object_type == req_object_type:
        score += 0.20
        matched_by.append("object_type_match")
        reasons.append(f"object_type {candidate_object_type}")

    # 5. motion_model match: +0.20
    if candidate_motion_model and candidate_motion_model == req_motion_model:
        score += 0.20
        matched_by.append("motion_model_match")
        reasons.append(f"motion_model {candidate_motion_model}")

    # 6. bad_prompt_fragment keyword match: +0.10
    if request.bad_prompt_fragment and candidate.patch_prompt:
        fragment_keywords = _extract_keywords(request.bad_prompt_fragment)
        if any(kw in (candidate.patch_prompt or "") for kw in fragment_keywords):
            score += 0.10
            matched_by.append("fragment_keyword")
            reasons.append("fragment keyword overlap")

    # 7. patch_context exists: +0.10
    if patch_context:
        score += 0.10

    # 8. Accepted attempt/case: +0.15
    if _is_accepted(session, candidate):
        score += 0.15
        matched_by.append("accepted")
        reasons.append("from accepted attempt/case")

    # 9. Non-generic patch: +0.10
    if candidate.patch_prompt and not _is_generic(candidate.patch_prompt):
        score += 0.10

    # 10. Recent (within 30 days): +0.05
    if _is_recent(session, candidate):
        score += 0.05

    # ── Deductions ─────────────────────────────────────────────────
    # custom failure_signature: -0.10
    if candidate.failure_signature == "custom":
        score -= 0.10
        reasons.append("custom failure (reduced)")

    # generic_object: -0.10
    if candidate_object_type == "generic_object":
        score -= 0.10
        reasons.append("generic object (reduced)")

    # unknown motion_model: -0.10
    if candidate_motion_model == "unknown":
        score -= 0.10
        reasons.append("unknown motion (reduced)")

    # patch_prompt too short: -0.05
    if candidate.patch_prompt and len(candidate.patch_prompt) < 20:
        score -= 0.05
        reasons.append("patch_prompt too short")

    # Generic phrases: -0.15
    if candidate.patch_prompt and any(phrase in candidate.patch_prompt for phrase in _GENERIC_PHRASES):
        score -= 0.15
        reasons.append("generic template phrase")

    candidate.ranking_score = max(0.0, min(1.0, round(score, 2)))
    candidate.matched_by = matched_by
    candidate.reason = "; ".join(reasons) if reasons else "no specific match"


def _dedup_candidates(candidates: list[RecommendedPatch]) -> list[RecommendedPatch]:
    """Dedup by patch_prompt, keeping the best ranking_score."""
    seen: dict[str, RecommendedPatch] = {}
    for c in candidates:
        key = c.patch_prompt or ""
        if key in seen:
            existing = seen[key]
            existing.duplicate_count += 1
            if c.case_id and c.case_id not in (existing.case_id or ""):
                existing.source_case_count += 1
            if c.ranking_score > existing.ranking_score:
                existing.ranking_score = c.ranking_score
                existing.reason = c.reason
                existing.matched_by = c.matched_by
                existing.case_id = c.case_id
                existing.case_title = c.case_title
                existing.attempt_id = c.attempt_id
                existing.confidence = c.confidence
        else:
            seen[key] = c
    return list(seen.values())


def _extract_patch_context(session: Session, patch_record_id: str | None) -> dict[str, Any] | None:
    """Extract patch_context from patch_packet_json."""
    if not patch_record_id:
        return None
    patch = session.get(PatchRecordModel, patch_record_id)
    if not patch or not patch.patch_packet_json:
        return None
    try:
        data = json.loads(patch.patch_packet_json)
        ctx = data.get("patch_context")
        return ctx if isinstance(ctx, dict) else None
    except (json.JSONDecodeError, AttributeError):
        return None


def _is_accepted(session: Session, candidate: RecommendedPatch) -> bool:
    """Check if the attempt or case is accepted."""
    if candidate.attempt_id:
        attempt = session.get(AttemptModel, candidate.attempt_id)
        if attempt and attempt.status == "ACCEPTED":
            return True
    if candidate.case_id:
        case = session.get(CaseModel, candidate.case_id)
        if case and case.status == "ACCEPTED":
            return True
    return False


def _is_recent(session: Session, candidate: RecommendedPatch) -> bool:
    """Check if the patch was created within 30 days."""
    if not candidate.patch_record_id:
        return False
    patch = session.get(PatchRecordModel, candidate.patch_record_id)
    if not patch or not patch.created_at:
        return False
    cutoff = datetime.now(UTC) - timedelta(days=30)
    created = patch.created_at if patch.created_at.tzinfo else patch.created_at.replace(tzinfo=UTC)
    return created >= cutoff


def _is_generic(prompt: str) -> bool:
    """Check if a patch_prompt is generic."""
    return any(phrase in prompt for phrase in _GENERIC_PHRASES)


def _extract_keywords(text: str) -> list[str]:
    """Extract simple keywords from text."""
    keywords = []
    for word in ("推拉窗", "窗扇", "轨道", "阀门", "中心轴", "门板", "铰链",
                 "抽屉", "滑轨", "按钮", "面板", "手指", "肢体", "手臂",
                 "场景", "服装", "布局", "参考图"):
        if word in text:
            keywords.append(word)
    return keywords


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
