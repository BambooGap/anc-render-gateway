from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT
from anc_gateway.render.job_manager import create_render_job, get_render_job, render_job_to_response
from anc_gateway.render.schemas import RenderJobCreateRequest, RenderJobStatus
from anc_gateway.storage.database import get_session


def test_create_render_job_starts_pending() -> None:
    packet = compile_render_packet(
        StateT(id="state_render_create", shot_id="shot_render_create"),
        RenderContract(shot_id="shot_render_create"),
        "她轻轻推开了推拉窗，风吹进房间。",
    )
    request = RenderJobCreateRequest(
        condition_hash=packet.condition_hash,
        compiled_prompt=packet.compiled_prompt,
        source_map=packet.source_map,
    )

    with get_session() as session:
        job = create_render_job(session, request, request_id="req-render-create")
        job_id = job.id
        response = render_job_to_response(job)

    assert response.status == RenderJobStatus.PENDING
    assert response.render_hash
    assert response.condition_hash == packet.condition_hash

    with get_session() as session:
        found = get_render_job(session, job_id)
        assert found is not None
        assert found.status == RenderJobStatus.PENDING.value
