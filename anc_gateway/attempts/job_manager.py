from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from anc_gateway.attempts.prompt_merge import build_next_attempt_prompt
from anc_gateway.attempts.schemas import (
    AttemptCreateRequest,
    AttemptResponse,
    AttemptStatus,
    CaseCreateRequest,
    CaseResponse,
    CaseStatus,
)
from anc_gateway.manual.schemas import ManualVendorPlatform
from anc_gateway.storage.models import AttemptModel, CaseModel
from anc_gateway.storage.serializers import dumps_json, source_map_to_json


def create_case(
    session: Session,
    request: CaseCreateRequest,
    request_id: str | None = None,
) -> CaseModel:
    title = request.title or _default_title(request.raw_prompt)
    model = CaseModel(
        request_id=request_id,
        title=title,
        raw_prompt=request.raw_prompt,
        platform=request.platform.value,
        status=CaseStatus.ACTIVE.value,
        metadata_json=dumps_json(request.metadata),
    )
    session.add(model)
    session.flush()
    return model


def get_case(session: Session, case_id: str) -> CaseModel | None:
    return session.get(CaseModel, case_id)


def list_recent_cases(session: Session, limit: int = 20) -> list[CaseModel]:
    bounded_limit = max(1, min(limit, 100))
    return list(
        session.scalars(select(CaseModel).order_by(CaseModel.created_at.desc()).limit(bounded_limit))
    )


def create_attempt(
    session: Session,
    case: CaseModel,
    request: AttemptCreateRequest,
    request_id: str | None = None,
) -> AttemptModel:
    previous = session.get(AttemptModel, request.previous_attempt_id) if request.previous_attempt_id else None
    raw_prompt = request.raw_prompt or (previous.raw_prompt if previous else case.raw_prompt)
    if previous and request.patch_packet is not None:
        base_prompt = previous.compiled_prompt or previous.raw_prompt
        raw_prompt = build_next_attempt_prompt(base_prompt, request.patch_packet)
    attempt_index = _next_attempt_index(session, case.id)
    status = AttemptStatus.COMPILED if request.compiled_prompt else AttemptStatus.DRAFT
    model = AttemptModel(
        case_id=case.id,
        request_id=request_id,
        attempt_index=attempt_index,
        status=status.value,
        raw_prompt=raw_prompt,
        compiled_prompt=request.compiled_prompt,
        condition_hash=request.condition_hash,
        source_map_json=dumps_json(source_map_to_json(request.source_map))
        if request.source_map
        else None,
        previous_attempt_id=previous.id if previous else None,
        notes=request.notes,
        metadata_json=dumps_json(request.metadata),
    )
    session.add(model)
    session.flush()
    case.current_attempt_id = model.id
    session.flush()
    return model


def get_attempt(session: Session, attempt_id: str) -> AttemptModel | None:
    return session.get(AttemptModel, attempt_id)


def list_case_attempts(session: Session, case_id: str) -> list[AttemptModel]:
    return list(
        session.scalars(
            select(AttemptModel)
            .where(AttemptModel.case_id == case_id)
            .order_by(AttemptModel.attempt_index.asc())
        )
    )


def link_attempt_manual_job(
    session: Session,
    attempt: AttemptModel,
    manual_job_id: str,
    result_video_uri: str | None = None,
) -> AttemptModel:
    attempt.manual_job_id = manual_job_id
    if result_video_uri:
        attempt.result_video_uri = result_video_uri
        attempt.status = AttemptStatus.VIDEO_COMPLETED.value
    else:
        attempt.status = AttemptStatus.MANUAL_JOB_CREATED.value
    session.flush()
    return attempt


def link_attempt_manual_audit(
    session: Session,
    attempt: AttemptModel,
    manual_audit_id: str,
    failure_record_id: str | None = None,
) -> AttemptModel:
    attempt.manual_audit_id = manual_audit_id
    attempt.failure_record_id = failure_record_id
    attempt.status = AttemptStatus.AUDITED.value
    session.flush()
    return attempt


def link_attempt_patch(
    session: Session,
    attempt: AttemptModel,
    patch_prompt: str,
    patch_record_id: str | None = None,
) -> AttemptModel:
    attempt.patch_prompt = patch_prompt
    attempt.patch_record_id = patch_record_id
    attempt.status = AttemptStatus.PATCHED.value
    session.flush()
    return attempt


def accept_attempt(
    session: Session,
    attempt: AttemptModel,
    accept_case: bool = True,
) -> AttemptModel:
    attempt.status = AttemptStatus.ACCEPTED.value
    if accept_case:
        case = session.get(CaseModel, attempt.case_id)
        if case is not None:
            case.status = CaseStatus.ACCEPTED.value
            case.current_attempt_id = attempt.id
    session.flush()
    return attempt


def reject_attempt(
    session: Session,
    attempt: AttemptModel,
    notes: str | None = None,
) -> AttemptModel:
    attempt.status = AttemptStatus.REJECTED.value
    attempt.notes = notes
    session.flush()
    return attempt


def archive_case(session: Session, case: CaseModel) -> CaseModel:
    case.status = CaseStatus.ARCHIVED.value
    session.flush()
    return case


def reopen_case(session: Session, case: CaseModel) -> CaseModel:
    case.status = CaseStatus.ACTIVE.value
    session.flush()
    return case


def case_to_response(case: CaseModel) -> CaseResponse:
    return CaseResponse(
        case_id=case.id,
        title=case.title,
        raw_prompt=case.raw_prompt,
        platform=ManualVendorPlatform(case.platform),
        status=CaseStatus(case.status),
        current_attempt_id=case.current_attempt_id,
        created_at=_datetime_to_iso(case.created_at),
        updated_at=_datetime_to_iso(case.updated_at),
    )


def attempt_to_response(attempt: AttemptModel) -> AttemptResponse:
    return AttemptResponse(
        attempt_id=attempt.id,
        case_id=attempt.case_id,
        attempt_index=attempt.attempt_index,
        status=AttemptStatus(attempt.status),
        raw_prompt=attempt.raw_prompt,
        compiled_prompt=attempt.compiled_prompt,
        condition_hash=attempt.condition_hash,
        manual_job_id=attempt.manual_job_id,
        manual_audit_id=attempt.manual_audit_id,
        failure_record_id=attempt.failure_record_id,
        patch_record_id=attempt.patch_record_id,
        patch_prompt=attempt.patch_prompt,
        result_video_uri=attempt.result_video_uri,
        notes=attempt.notes,
        created_at=_datetime_to_iso(attempt.created_at),
        updated_at=_datetime_to_iso(attempt.updated_at),
    )


def _next_attempt_index(session: Session, case_id: str) -> int:
    current = session.scalar(
        select(func.max(AttemptModel.attempt_index)).where(AttemptModel.case_id == case_id)
    )
    return int(current or 0) + 1


def _default_title(raw_prompt: str) -> str:
    stripped = raw_prompt.strip()
    return stripped[:40] or "Untitled case"


def _datetime_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
