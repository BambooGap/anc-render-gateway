import pytest

from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT
from anc_gateway.render.job_manager import create_render_job
from anc_gateway.render.schemas import RenderJobCreateRequest
from anc_gateway.storage.database import get_session
from anc_gateway.vendors.fake_http_adapter import FakeHTTPVendorAdapter


def test_fake_http_adapter_submit_uses_mock_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FAKE_HTTP_API_KEY", "fake-secret")
    packet = compile_render_packet(
        StateT(id="state_fake_http", shot_id="shot_fake_http"),
        RenderContract(shot_id="shot_fake_http"),
        "她轻轻推开了推拉窗，风吹进房间。",
    )
    request = RenderJobCreateRequest(
        condition_hash=packet.condition_hash,
        compiled_prompt=packet.compiled_prompt,
        source_map=packet.source_map,
        vendor="fake-http",
        model="fake-http-video-v1",
    )

    with get_session() as session:
        job = create_render_job(session, request)
        result = FakeHTTPVendorAdapter().submit_render_job(job)

    assert result.external_job_id.startswith("fake_http_external_")
    assert result.status == "SUCCEEDED"
    assert result.video_uri is not None
    assert result.video_uri.startswith("fake-http://renders/")


def test_fake_http_adapter_status_and_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_HTTP_API_KEY", "fake-secret")
    adapter = FakeHTTPVendorAdapter()

    status = adapter.get_render_status("fake_http_external_001")
    cancel = adapter.cancel_render_job("fake_http_external_001")

    assert status.status == "SUCCEEDED"
    assert status.video_uri == "fake-http://renders/fake_http_external_001.mp4"
    assert cancel.cancelled is True
