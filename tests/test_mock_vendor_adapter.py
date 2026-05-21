from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT
from anc_gateway.render.job_manager import create_render_job
from anc_gateway.render.schemas import RenderJobCreateRequest
from anc_gateway.storage.database import get_session
from anc_gateway.vendors.mock_adapter import MockVendorAdapter


def test_mock_adapter_submit_returns_external_id_and_video_uri() -> None:
    packet = compile_render_packet(
        StateT(id="state_vendor_mock", shot_id="shot_vendor_mock"),
        RenderContract(shot_id="shot_vendor_mock"),
        "她轻轻推开了推拉窗，风吹进房间。",
    )
    request = RenderJobCreateRequest(
        condition_hash=packet.condition_hash,
        compiled_prompt=packet.compiled_prompt,
        source_map=packet.source_map,
    )

    with get_session() as session:
        job = create_render_job(session, request)
        result = MockVendorAdapter().submit_render_job(job)

    assert result.external_job_id.startswith("mock_external_")
    assert result.status == "SUCCEEDED"
    assert result.video_uri is not None
    assert result.video_uri.startswith("mock://renders/")


def test_mock_adapter_status_and_cancel() -> None:
    adapter = MockVendorAdapter()

    status = adapter.get_render_status("mock_external_001")
    cancel = adapter.cancel_render_job("mock_external_001")

    assert status.status == "SUCCEEDED"
    assert status.video_uri == "mock://renders/mock_external_001.mp4"
    assert cancel.cancelled is True
