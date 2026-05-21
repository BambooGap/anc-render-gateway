from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT
from anc_gateway.manual.job_manager import create_manual_job, manual_job_to_response
from anc_gateway.manual.schemas import ManualJobCreateRequest, ManualJobStatus, ManualVendorPlatform
from anc_gateway.storage.database import get_session


def test_create_manual_job_waits_for_user_and_includes_prompt() -> None:
    packet = compile_render_packet(
        StateT(id="state_manual_create", shot_id="shot_manual_create"),
        RenderContract(shot_id="shot_manual_create"),
        "她轻轻推开了推拉窗，风吹进房间。",
    )
    request = ManualJobCreateRequest(
        condition_hash=packet.condition_hash,
        compiled_prompt=packet.compiled_prompt,
        source_map=packet.source_map,
        platform=ManualVendorPlatform.GENERIC_WEB,
    )

    with get_session() as session:
        job = create_manual_job(session, request, request_id="req-manual-create")
        response = manual_job_to_response(job)

    assert response.status == ManualJobStatus.WAITING_FOR_USER
    assert response.platform == ManualVendorPlatform.GENERIC_WEB
    assert packet.compiled_prompt in response.copy_instructions
    assert response.result_video_uri is None
