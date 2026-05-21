from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from anc_gateway.manual.instructions import build_manual_instructions
from anc_gateway.manual.schemas import (
    CompleteManualJobRequest,
    ManualJobCreateRequest,
    ManualJobResponse,
    ManualJobStatus,
    ManualVendorPlatform,
)
from anc_gateway.storage.models import ManualJobModel
from anc_gateway.storage.serializers import dumps_json, source_map_to_json


def create_manual_job(
    session: Session,
    request: ManualJobCreateRequest,
    request_id: str | None = None,
) -> ManualJobModel:
    instructions = build_manual_instructions(
        request.platform,
        request.compiled_prompt,
        request.visual_anchor_uri,
    )
    model = ManualJobModel(
        request_id=request_id,
        platform=request.platform.value,
        status=ManualJobStatus.WAITING_FOR_USER.value,
        condition_hash=request.condition_hash,
        compiled_prompt=request.compiled_prompt,
        source_map_json=dumps_json(source_map_to_json(request.source_map)),
        visual_anchor_uri=request.visual_anchor_uri,
        copy_instructions=instructions,
        user_notes=request.notes,
        metadata_json=dumps_json(request.metadata),
    )
    session.add(model)
    session.flush()
    return model


def get_manual_job(session: Session, manual_job_id: str) -> ManualJobModel | None:
    return session.get(ManualJobModel, manual_job_id)


def complete_manual_job(
    session: Session,
    job: ManualJobModel,
    request: CompleteManualJobRequest,
) -> ManualJobModel:
    job.status = request.status.value
    job.result_video_uri = request.result_video_uri
    job.user_notes = request.user_notes
    session.flush()
    return job


def fail_manual_job(
    session: Session,
    job: ManualJobModel,
    user_notes: str | None = None,
) -> ManualJobModel:
    job.status = ManualJobStatus.FAILED.value
    job.user_notes = user_notes
    session.flush()
    return job


def list_recent_manual_jobs(session: Session, limit: int = 20) -> list[ManualJobModel]:
    bounded_limit = max(1, min(limit, 100))
    return list(
        session.scalars(
            select(ManualJobModel).order_by(ManualJobModel.created_at.desc()).limit(bounded_limit)
        )
    )


def manual_job_to_response(job: ManualJobModel) -> ManualJobResponse:
    return ManualJobResponse(
        manual_job_id=job.id,
        status=ManualJobStatus(job.status),
        platform=ManualVendorPlatform(job.platform),
        condition_hash=job.condition_hash,
        compiled_prompt=job.compiled_prompt,
        copy_instructions=job.copy_instructions,
        visual_anchor_uri=job.visual_anchor_uri,
        result_video_uri=job.result_video_uri,
        user_notes=job.user_notes,
        created_at=_datetime_to_iso(job.created_at),
        updated_at=_datetime_to_iso(job.updated_at),
    )


def _datetime_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
