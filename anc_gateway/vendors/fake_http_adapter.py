from __future__ import annotations

from uuid import uuid4

import httpx

from anc_gateway.storage.models import RenderJobModel
from anc_gateway.vendors.base import VendorCancelResult, VendorRenderStatus, VendorSubmitResult
from anc_gateway.vendors.config import VendorHTTPConfig
from anc_gateway.vendors.http_base import HTTPVendorAdapterBase
from anc_gateway.vendors.status_mapping import map_vendor_status


class FakeHTTPVendorAdapter(HTTPVendorAdapterBase):
    def __init__(self) -> None:
        self._external_job_id = ""
        super().__init__(
            VendorHTTPConfig(
                vendor="fake-http",
                model="fake-http-video-v1",
                base_url="https://fake-http.vendor.local",
                api_key_env="FAKE_HTTP_API_KEY",
                timeout_seconds=10.0,
            ),
            transport=httpx.MockTransport(self._handle_request),
        )

    def submit_render_job(self, job: RenderJobModel) -> VendorSubmitResult:
        response = self.post_json(
            "/renders",
            {
                "local_job_id": job.id,
                "condition_hash": job.condition_hash,
                "compiled_prompt": job.compiled_prompt,
                "model": job.model,
            },
        )
        return VendorSubmitResult(
            external_job_id=str(response["external_job_id"]),
            status=map_vendor_status(str(response["status"])).value,
            video_uri=str(response["video_uri"]) if response.get("video_uri") else None,
            raw_response=response,
        )

    def get_render_status(self, external_job_id: str) -> VendorRenderStatus:
        response = self.get_json(f"/renders/{external_job_id}")
        return VendorRenderStatus(
            external_job_id=str(response["external_job_id"]),
            status=map_vendor_status(str(response["status"])).value,
            video_uri=str(response["video_uri"]) if response.get("video_uri") else None,
            error_message=str(response["error_message"]) if response.get("error_message") else None,
            raw_response=response,
        )

    def cancel_render_job(self, external_job_id: str) -> VendorCancelResult:
        response = self.post_json(f"/renders/{external_job_id}/cancel", {})
        return VendorCancelResult(
            external_job_id=str(response["external_job_id"]),
            cancelled=bool(response["cancelled"]),
            raw_response=response,
        )

    def _handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/renders":
            self._external_job_id = f"fake_http_external_{uuid4()}"
            return httpx.Response(
                200,
                json={
                    "external_job_id": self._external_job_id,
                    "status": "succeeded",
                    "video_uri": f"fake-http://renders/{self._external_job_id}.mp4",
                    "raw": {"transport": "mock"},
                },
            )
        if request.method == "GET" and request.url.path.startswith("/renders/"):
            external_job_id = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(
                200,
                json={
                    "external_job_id": external_job_id,
                    "status": "succeeded",
                    "video_uri": f"fake-http://renders/{external_job_id}.mp4",
                    "error_message": None,
                },
            )
        if request.method == "POST" and request.url.path.endswith("/cancel"):
            external_job_id = request.url.path.split("/")[-2]
            return httpx.Response(
                200,
                json={
                    "external_job_id": external_job_id,
                    "cancelled": True,
                },
            )
        return httpx.Response(404, json={"error": "not found"})
