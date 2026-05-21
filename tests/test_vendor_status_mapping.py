import pytest

from anc_gateway.render.schemas import RenderJobStatus
from anc_gateway.vendors.errors import VendorResponseParseError
from anc_gateway.vendors.status_mapping import map_vendor_status


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        ("pending", RenderJobStatus.PENDING),
        ("queued", RenderJobStatus.PENDING),
        ("running", RenderJobStatus.RUNNING),
        ("processing", RenderJobStatus.RUNNING),
        ("succeeded", RenderJobStatus.SUCCEEDED),
        ("success", RenderJobStatus.SUCCEEDED),
        ("completed", RenderJobStatus.SUCCEEDED),
        ("failed", RenderJobStatus.FAILED),
        ("error", RenderJobStatus.FAILED),
        ("cancelled", RenderJobStatus.CANCELLED),
        ("canceled", RenderJobStatus.CANCELLED),
    ],
)
def test_map_vendor_status(raw_status: str, expected: RenderJobStatus) -> None:
    assert map_vendor_status(raw_status) == expected


def test_map_vendor_status_unknown_raises() -> None:
    with pytest.raises(VendorResponseParseError):
        map_vendor_status("half-baked")
