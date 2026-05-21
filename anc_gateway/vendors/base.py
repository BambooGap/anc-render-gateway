from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from anc_gateway.storage.models import RenderJobModel


class VendorSubmitResult(BaseModel):
    external_job_id: str
    status: str
    video_uri: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class VendorRenderStatus(BaseModel):
    external_job_id: str
    status: str
    video_uri: str | None = None
    error_message: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class VendorCancelResult(BaseModel):
    external_job_id: str
    cancelled: bool
    raw_response: dict[str, Any] = Field(default_factory=dict)


class RenderVendorAdapter(ABC):
    @abstractmethod
    def submit_render_job(self, job: RenderJobModel) -> VendorSubmitResult:
        raise NotImplementedError

    @abstractmethod
    def get_render_status(self, external_job_id: str) -> VendorRenderStatus:
        raise NotImplementedError

    @abstractmethod
    def cancel_render_job(self, external_job_id: str) -> VendorCancelResult:
        raise NotImplementedError
