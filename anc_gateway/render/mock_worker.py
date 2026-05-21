from __future__ import annotations

from sqlalchemy.orm import Session

from anc_gateway.render.job_manager import update_render_job_status
from anc_gateway.render.schemas import RenderJobStatus
from anc_gateway.storage.models import RenderJobModel


def run_mock_render(session: Session, job: RenderJobModel) -> RenderJobModel:
    update_render_job_status(session, job, RenderJobStatus.RUNNING)
    return update_render_job_status(
        session,
        job,
        RenderJobStatus.SUCCEEDED,
        video_uri=f"mock://renders/{job.id}.mp4",
        error_message=None,
    )


def fail_mock_render(
    session: Session,
    job: RenderJobModel,
    error_message: str | None = None,
) -> RenderJobModel:
    return update_render_job_status(
        session,
        job,
        RenderJobStatus.FAILED,
        video_uri=None,
        error_message=error_message or "Mock render failed by request.",
    )
