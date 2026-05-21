import json

from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT
from anc_gateway.storage.database import get_session
from anc_gateway.storage.repositories import get_compile_job_by_condition_hash, save_compile_job


def test_save_compile_job_and_lookup_by_condition_hash() -> None:
    state = StateT(id="state_storage_compile", shot_id="shot_storage_compile")
    contract = RenderContract(shot_id="shot_storage_compile")
    raw_prompt = "她轻轻推开了推拉窗，风吹进房间。"
    packet = compile_render_packet(state, contract, raw_prompt)

    with get_session() as session:
        saved = save_compile_job(session, raw_prompt, state, contract, packet, request_id="req-storage")
        saved_id = saved.id

    with get_session() as session:
        found = get_compile_job_by_condition_hash(session, packet.condition_hash)
        assert found is not None
        assert found.id == saved_id
        source_map_json = json.loads(found.source_map_json)
        assert "frag_001" in source_map_json["fragments"]
        assert source_map_json["fragments"]["frag_001"]["original_text"] == "她轻轻推开了推拉窗"
