from __future__ import annotations

from anc_gateway.render.schemas import RenderJobStatus
from anc_gateway.vendors.errors import VendorResponseParseError

_STATUS_MAP = {
    "pending": RenderJobStatus.PENDING,
    "queued": RenderJobStatus.PENDING,
    "running": RenderJobStatus.RUNNING,
    "processing": RenderJobStatus.RUNNING,
    "succeeded": RenderJobStatus.SUCCEEDED,
    "success": RenderJobStatus.SUCCEEDED,
    "completed": RenderJobStatus.SUCCEEDED,
    "failed": RenderJobStatus.FAILED,
    "error": RenderJobStatus.FAILED,
    "cancelled": RenderJobStatus.CANCELLED,
    "canceled": RenderJobStatus.CANCELLED,
}


def map_vendor_status(raw_status: str) -> RenderJobStatus:
    normalized = raw_status.strip().lower()
    try:
        return _STATUS_MAP[normalized]
    except KeyError as exc:
        raise VendorResponseParseError(f"Unknown vendor render status: {raw_status}") from exc
