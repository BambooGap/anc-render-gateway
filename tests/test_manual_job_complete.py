from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT
from anc_gateway.manual.job_manager import (
    complete_manual_job,
    create_manual_job,
    fail_manual_job,
    get_manual_job,
    list_recent_manual_jobs,
    manual_job_to_response,
)
from anc_gateway.manual.schemas import (
    CompleteManualJobRequest,
    ManualJobCreateRequest,
    ManualJobStatus,
    ManualVendorPlatform,
)
from anc_gateway.storage.database import get_session


def _create_manual_job() -> str:
    packet = compile_render_packet(
        StateT(id="state_manual_complete", shot_id="shot_manual_complete"),
        RenderContract(shot_id="shot_manual_complete"),
        "她轻轻推开了推拉窗，风吹进房间。",
    )
    request = ManualJobCreateRequest(
        condition_hash=packet.condition_hash,
        compiled_prompt=packet.compiled_prompt,
        source_map=packet.source_map,
        platform=ManualVendorPlatform.JIMENG_WEB,
    )
    with get_session() as session:
        return create_manual_job(session, request).id


def test_complete_manual_job_saves_video_uri_and_notes() -> None:
    manual_job_id = _create_manual_job()

    with get_session() as session:
        job = get_manual_job(session, manual_job_id)
        assert job is not None
        completed = complete_manual_job(
            session,
            job,
            CompleteManualJobRequest(
                result_video_uri="file:///tmp/manual_video.mp4",
                user_notes="looks usable",
            ),
        )
        response = manual_job_to_response(completed)

    assert response.status == ManualJobStatus.COMPLETED
    assert response.result_video_uri == "file:///tmp/manual_video.mp4"
    assert response.user_notes == "looks usable"


def test_fail_manual_job_marks_failed() -> None:
    manual_job_id = _create_manual_job()

    with get_session() as session:
        job = get_manual_job(session, manual_job_id)
        assert job is not None
        failed = fail_manual_job(session, job, user_notes="platform quota ran out")
        response = manual_job_to_response(failed)

    assert response.status == ManualJobStatus.FAILED
    assert response.user_notes == "platform quota ran out"


def test_recent_manual_jobs_returns_list() -> None:
    manual_job_id = _create_manual_job()

    with get_session() as session:
        recent = list_recent_manual_jobs(session, limit=20)

    assert len(recent) == 1
    assert recent[0].id == manual_job_id
