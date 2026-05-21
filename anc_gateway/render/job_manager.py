from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from anc_gateway.render.hash import compute_render_hash
from anc_gateway.render.schemas import RenderJobCreateRequest, RenderJobResponse, RenderJobStatus
from anc_gateway.storage.models import RenderJobModel
from anc_gateway.storage.serializers import dumps_json, source_map_to_json


def create_render_job(
    session: Session,
    request: RenderJobCreateRequest,
    request_id: str | None = None,
) -> RenderJobModel:
    render_hash = compute_render_hash(
        condition_hash=request.condition_hash,
        vendor=request.vendor,
        model=request.model,
        visual_anchor_uri=request.visual_anchor_uri,
        metadata=request.metadata,
    )
    model = RenderJobModel(
        request_id=request_id,
        condition_hash=request.condition_hash,
        render_hash=render_hash,
        vendor=request.vendor,
        model=request.model,
        status=RenderJobStatus.PENDING.value,
        compiled_prompt=request.compiled_prompt,
        source_map_json=dumps_json(source_map_to_json(request.source_map)),
        visual_anchor_uri=request.visual_anchor_uri,
        metadata_json=dumps_json(request.metadata),
    )
    session.add(model)
    session.flush()
    return model


def get_render_job(session: Session, job_id: str) -> RenderJobModel | None:
    return session.get(RenderJobModel, job_id)


def list_recent_render_jobs(session: Session, limit: int = 20) -> list[RenderJobModel]:
    bounded_limit = max(1, min(limit, 100))
    return list(
        session.scalars(
            select(RenderJobModel).order_by(RenderJobModel.created_at.desc()).limit(bounded_limit)
        )
    )


def update_render_job_status(
    session: Session,
    job: RenderJobModel,
    status: RenderJobStatus,
    video_uri: str | None = None,
    error_message: str | None = None,
) -> RenderJobModel:
    job.status = status.value
    job.video_uri = video_uri
    job.error_message = error_message
    session.flush()
    return job


def render_job_to_response(job: RenderJobModel) -> RenderJobResponse:
    return RenderJobResponse(
        job_id=job.id,
        status=RenderJobStatus(job.status),
        condition_hash=job.condition_hash,
        render_hash=job.render_hash,
        vendor=job.vendor,
        model=job.model,
        video_uri=job.video_uri,
        error_message=job.error_message,
        created_at=_datetime_to_iso(job.created_at),
        updated_at=_datetime_to_iso(job.updated_at),
    )


def _datetime_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
