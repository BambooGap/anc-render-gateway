from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from anc_gateway.render.hash import compute_render_hash
from anc_gateway.render.schemas import RenderJobCreateRequest, RenderJobResponse, RenderJobStatus
from anc_gateway.storage.models import RenderJobModel
from anc_gateway.storage.serializers import dumps_json, source_map_to_json
from anc_gateway.vendors.registry import VendorAdapterRegistry, default_vendor_registry


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


def submit_render_job_to_vendor(
    session: Session,
    job: RenderJobModel,
    registry: VendorAdapterRegistry = default_vendor_registry,
) -> RenderJobModel:
    adapter = registry.get(job.vendor)
    result = adapter.submit_render_job(job)
    job.external_job_id = result.external_job_id
    job.status = _vendor_status_to_render_status(result.status).value
    job.video_uri = result.video_uri
    job.error_message = None
    metadata = _load_metadata(job.metadata_json)
    metadata["external_job_id"] = result.external_job_id
    metadata["vendor_submit_raw_response"] = result.raw_response
    job.metadata_json = dumps_json(metadata)
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


def _vendor_status_to_render_status(status: str) -> RenderJobStatus:
    normalized = status.upper()
    if normalized in RenderJobStatus.__members__:
        return RenderJobStatus[normalized]
    if normalized in {"QUEUED", "SUBMITTED"}:
        return RenderJobStatus.PENDING
    return RenderJobStatus.RUNNING


def _load_metadata(metadata_json: str) -> dict[str, Any]:
    try:
        value = json.loads(metadata_json)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
