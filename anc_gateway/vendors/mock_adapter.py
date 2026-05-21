from __future__ import annotations

from uuid import uuid4

from anc_gateway.storage.models import RenderJobModel
from anc_gateway.vendors.base import (
    RenderVendorAdapter,
    VendorCancelResult,
    VendorRenderStatus,
    VendorSubmitResult,
)


class MockVendorAdapter(RenderVendorAdapter):
    def submit_render_job(self, job: RenderJobModel) -> VendorSubmitResult:
        external_job_id = f"mock_external_{uuid4()}"
        return VendorSubmitResult(
            external_job_id=external_job_id,
            status="SUCCEEDED",
            video_uri=f"mock://renders/{external_job_id}.mp4",
            raw_response={
                "vendor": "mock",
                "local_job_id": job.id,
                "render_hash": job.render_hash,
            },
        )

    def get_render_status(self, external_job_id: str) -> VendorRenderStatus:
        return VendorRenderStatus(
            external_job_id=external_job_id,
            status="SUCCEEDED",
            video_uri=f"mock://renders/{external_job_id}.mp4",
            raw_response={"vendor": "mock"},
        )

    def cancel_render_job(self, external_job_id: str) -> VendorCancelResult:
        return VendorCancelResult(
            external_job_id=external_job_id,
            cancelled=True,
            raw_response={"vendor": "mock"},
        )
