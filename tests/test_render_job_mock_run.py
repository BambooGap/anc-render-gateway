from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT
from anc_gateway.render.job_manager import create_render_job, get_render_job, render_job_to_response
from anc_gateway.render.mock_worker import fail_mock_render, run_mock_render
from anc_gateway.render.schemas import RenderJobCreateRequest, RenderJobStatus
from anc_gateway.storage.database import get_session


def _create_job() -> str:
    packet = compile_render_packet(
        StateT(id="state_render_run", shot_id="shot_render_run"),
        RenderContract(shot_id="shot_render_run"),
        "她轻轻推开了推拉窗，风吹进房间。",
    )
    request = RenderJobCreateRequest(
        condition_hash=packet.condition_hash,
        compiled_prompt=packet.compiled_prompt,
        source_map=packet.source_map,
    )
    with get_session() as session:
        return create_render_job(session, request).id


def test_run_mock_render_succeeds_with_mock_video_uri() -> None:
    job_id = _create_job()

    with get_session() as session:
        job = get_render_job(session, job_id)
        assert job is not None
        response = render_job_to_response(run_mock_render(session, job))

    assert response.status == RenderJobStatus.SUCCEEDED
    assert response.video_uri is not None
    assert response.video_uri.startswith("mock://renders/")


def test_fail_mock_render_marks_job_failed() -> None:
    job_id = _create_job()

    with get_session() as session:
        job = get_render_job(session, job_id)
        assert job is not None
        response = render_job_to_response(fail_mock_render(session, job, "boom"))

    assert response.status == RenderJobStatus.FAILED
    assert response.error_message == "boom"
